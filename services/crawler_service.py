import os
import re
import base64
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from repositories.auction_repository import AuctionRepository
from utils.env_utils import is_oracle_instance
from utils.date_utils import convert_yyyymmdd_to_dotted
from utils.naver_utils import get_coordinates
from utils.address_utils import build_full_address


class CrawlerService:
    """
    법원경매 사이트에서 매물 정보를 크롤링하는 서비스.
    기존 main.py 크롤링 로직을 재구성하여
    new_auctions, updated_auctions 리스트를 반환합니다.
    """

    def __init__(self, auction_repo: AuctionRepository):
        self.repo = auction_repo

    # ---------------------------
    # 🔹 Helper Functions
    # ---------------------------

    def compare_case_id_duplicated(
        self, data: List[Dict], case_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """사건번호 중복 확인"""
        for item in data:
            if item["case_id"] == case_id:
                return True, item
        return False, None

    def extract_image_list(
        self, case_id: str, court_code: str, sido_code: str, sigu_code: str
    ):
        """
        법원경매 물건 이미지 목록 조회
        """
        url = "https://www.courtauction.go.kr/pgj/pgj15B/selectAuctnCsSrchRslt.on"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.courtauction.go.kr/",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
        data = {
            "dma_srchGdsDtlSrch": {
                "csNo": case_id,  # 사건번호
                "cortOfcCd": court_code,  # 담당법원코드
                "dspslGdsSeq": "1",
                "pgmId": "PGJ151F01",
                "srchInfo": {
                    "rletDspslSpcCondCd": "",
                    "bidDvsCd": "000331",
                    "mvprpRletDvsCd": "00031R",
                    "cortAuctnSrchCondCd": "0004601",
                    "rprsAdongSdCd": sido_code,
                    "rprsAdongSggCd": sigu_code,
                    "rprsAdongEmdCd": "",
                    "rdnmSdCd": "",
                    "rdnmSggCd": "",
                    "rdnmNo": "",
                    "mvprpDspslPlcAdongSdCd": "",
                    "mvprpDspslPlcAdongSggCd": "",
                    "mvprpDspslPlcAdongEmdCd": "",
                    "rdDspslPlcAdongSdCd": "",
                    "rdDspslPlcAdongSggCd": "",
                    "rdDspslPlcAdongEmdCd": "",
                    "cortOfcCd": court_code,
                    "jdbnCd": "",
                    "execrOfcDvsCd": "",
                    "lclDspslGdsLstUsgCd": "20000",
                    "mclDspslGdsLstUsgCd": "20100",
                    "sclDspslGdsLstUsgCd": "20104",
                    "cortAuctnMbrsId": "",
                    "aeeEvlAmtMin": "",
                    "aeeEvlAmtMax": "",
                    "lwsDspslPrcRateMin": "",
                    "lwsDspslPrcRateMax": "",
                    "flbdNcntMin": "",
                    "flbdNcntMax": "",
                    "objctArDtsMin": "",
                    "objctArDtsMax": "",
                    "mvprpArtclKndCd": "",
                    "mvprpArtclNm": "",
                    "mvprpAtchmPlcTypCd": "",
                    "notifyLoc": "on",
                    "lafjOrderBy": "",
                    "pgmId": "PGJ151F01",
                    "csNo": "",
                    "cortStDvs": "2",
                    "statNum": 1,
                    "bidBgngYmd": "",
                    "bidEndYmd": "",
                    "dspslDxdyYmd": "",
                    "fstDspslHm": "",
                    "scndDspslHm": "",
                    "thrdDspslHm": "",
                    "fothDspslHm": "",
                    "dspslPlcNm": "",
                    "lwsDspslPrcMin": "",
                    "lwsDspslPrcMax": "",
                    "grbxTypCd": "",
                    "gdsVendNm": "",
                    "fuelKndCd": "",
                    "carMdyrMax": "",
                    "carMdyrMin": "",
                    "carMdlNm": "",
                    "sideDvsCd": "2",
                    "menuNm": "물건상세검색",
                },
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get("data", {})
                if (
                    data
                    and "dma_result" in data
                    and len(data["dma_result"].get("csPicLst", [])) > 0
                ):
                    return data["dma_result"]["csPicLst"]
                else:
                    print(f"⚠️ 이미지 없음: {case_id}")
                    return []
            else:
                print(f"❌ 이미지 요청 실패: {response.status_code}")
                return []
        except Exception as e:
            print(f"❗ 이미지 추출 중 오류 ({case_id}): {e}")
            return []

    # ---------------------------
    # 🔸 Main Crawler
    # ---------------------------

    def crawl_new_auctions(
        self, detect_target: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """법원경매 사이트에서 신규 및 갱신 매물 수집"""
        raw_results = []
        today = datetime.now()
        start_date = today - timedelta(days=15)
        end_date = today + timedelta(days=15)

        today_iso = today.isoformat()
        start_iso = start_date.isoformat()

        # supabase 기존 데이터 로드
        exist_data = self.repo.fetch_by_date_range(start_iso, today_iso)

        new_auctions: List[Dict] = []
        updated_auctions: List[Dict] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.courtauction.go.kr/",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }

        url = "https://www.courtauction.go.kr/pgj/pgjsearch/searchControllerMain.on"

        for target in detect_target:
            start_date_str = today.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            data = {
                "dma_pageInfo": {
                    "pageNo": 1,
                    "pageSize": 50,
                    "bfPageNo": "",
                    "startRowNo": "",
                    "totalCnt": "",
                    "totalYn": "Y",
                    "groupTotalCount": "",
                },
                "dma_srchGdsDtlSrchInfo": {
                    "rletDspslSpcCondCd": "",
                    "bidDvsCd": "000331",
                    "mvprpRletDvsCd": "00031R",
                    "cortAuctnSrchCondCd": "0004601",
                    "rprsAdongSdCd": target["sido_code"],
                    "rprsAdongSggCd": target["sigu_code"],
                    "rprsAdongEmdCd": "",
                    "rdnmSdCd": "",
                    "rdnmSggCd": "",
                    "rdnmNo": "",
                    "mvprpDspslPlcAdongSdCd": "",
                    "mvprpDspslPlcAdongSggCd": "",
                    "mvprpDspslPlcAdongEmdCd": "",
                    "rdDspslPlcAdongSdCd": "",
                    "rdDspslPlcAdongSggCd": "",
                    "rdDspslPlcAdongEmdCd": "",
                    "cortOfcCd": "B000210",
                    "jdbnCd": "",
                    "execrOfcDvsCd": "",
                    "lclDspslGdsLstUsgCd": "20000",
                    "mclDspslGdsLstUsgCd": "20100",
                    "sclDspslGdsLstUsgCd": "20104",
                    "cortAuctnMbrsId": "",
                    "aeeEvlAmtMin": "",
                    "aeeEvlAmtMax": "",
                    "lwsDspslPrcRateMin": "",
                    "lwsDspslPrcRateMax": "",
                    "flbdNcntMin": "",
                    "flbdNcntMax": "",
                    "objctArDtsMin": "",
                    "objctArDtsMax": "",
                    "mvprpArtclKndCd": "",
                    "mvprpArtclNm": "",
                    "mvprpAtchmPlcTypCd": "",
                    "notifyLoc": "on",
                    "lafjOrderBy": "",
                    "pgmId": "PGJ151F01",
                    "csNo": "",
                    "cortStDvs": "2",
                    "statNum": 1,
                    "bidBgngYmd": start_date_str,
                    "bidEndYmd": end_date_str,
                    "dspslDxdyYmd": "",
                    "fstDspslHm": "",
                    "scndDspslHm": "",
                    "thrdDspslHm": "",
                    "fothDspslHm": "",
                    "dspslPlcNm": "",
                    "lwsDspslPrcMin": "",
                    "lwsDspslPrcMax": "",
                    "grbxTypCd": "",
                    "gdsVendNm": "",
                    "fuelKndCd": "",
                    "carMdyrMax": "",
                    "carMdyrMin": "",
                    "carMdlNm": "",
                },
            }

            try:
                response = requests.post(
                    url,
                    json=data,
                    headers=headers,
                )
                if response.status_code != 200:
                    print(f"❌ 요청 실패: {response.status_code}")
                    continue

                json_data = response.json()
                search_results = json_data.get("data", {}).get("dlt_srchResult", [])
                raw_results.extend(
                    [
                        {
                            **item,
                            "sido_code": target["sido_code"],
                            "sigu_code": target["sigu_code"],
                        }
                        for item in search_results
                    ]
                )
                print(
                    f"📑 {len(search_results)}건 검색됨 (sido: {target['sido_code']}, sigu: {target['sigu_code']})"
                )

                for item in search_results:
                    case_id = item["srnSaNo"]
                    failed_count = int(item.get("yuchalCnt", 0))
                    is_exist, existing_item = self.compare_case_id_duplicated(
                        exist_data, case_id
                    )

                    status = "신건"
                    if failed_count > 0:
                        status = "유찰"

                    # 신규 매물
                    if not is_exist:
                        images = self.extract_image_list(
                            case_id,
                            item["boCd"],
                            target["sido_code"],
                            target["sigu_code"],
                        )
                        if not images:
                            continue

                        # 대표 이미지 찾기
                        image = next(
                            (img for img in images if img.get("pageSeq") == "1"),
                            images[0],
                        )
                        image_data = base64.b64decode(image["picFile"])

                        # 이미지 저장
                        save_dir = (
                            f"/var/www/images/auctions/{image['csNo']}"
                            if is_oracle_instance()
                            else f"./images/auctions/{image['csNo']}"
                        )
                        os.makedirs(save_dir, exist_ok=True)

                        file_path = os.path.join(
                            save_dir, f"{image['cortAuctnPicSeq']}.jpg"
                        )
                        file_url = f"http://oracle.artchive.in/images/auctions/{image['csNo']}/{image['cortAuctnPicSeq']}.jpg"

                        with open(file_path, "wb") as f:
                            f.write(image_data)

                        area = re.search(r"(\d+\.\d+)", item.get("pjbBuldList", ""))
                        area_value = area.group(1) if area else None

                        auction_date = convert_yyyymmdd_to_dotted(item["maeGiil"])

                        full_addr = build_full_address(item)
                        longitude, latitude, jibun_address, road_address = (
                            get_coordinates(full_addr)
                        )

                        auction = {
                            "court": item.get("jiwonNm"),
                            "case_id": case_id,
                            "category": item.get("dspslUsgNm"),
                            "address": item.get("printSt"),
                            "area": area_value,
                            "estimated_price": item.get("gamevalAmt"),
                            "minimum_price": item.get("notifyMinmaePrice1"),
                            "etc": item.get("mulBigo"),
                            "status": status,
                            "failed_auction_count": failed_count,
                            "auction_date": auction_date,
                            "sido_code": target["sido_code"],
                            "sigu_code": target["sigu_code"],
                            "thumbnail_src": file_url,
                            "rd1_nm": item.get("rd1Nm"),
                            "rd2_nm": item.get("rd2Nm"),
                            "rd_eub_myun": item.get("rdEubMyun"),
                            "rd_nm": item.get("rdNm"),
                            "buld_no": item.get("buldNo"),
                            "rd_addr_sub": item.get("rdAddrSub"),
                            "bg_place_rd_all_addr": item.get("bgPlaceRdAllAddr"),
                            "conv_addr": item.get("convAddr"),
                            "buld_nm": item.get("buldNm"),
                            "buld_list": item.get("buldList"),
                            "srch_hjgu_lotno": item.get("srchHjguLotno"),
                            "srch_hjgu_rd_cd": item.get("srchHjguRdCd"),
                            "srch_hjgu_dong_cd": item.get("srchHjguDongCd"),
                            "docid": item.get("docid"),
                            "sa_no": item.get("saNo"),
                            "bo_cd": item.get("boCd"),
                            "latitude": latitude,
                            "longitude": longitude,
                            "jibun_address": jibun_address,
                            "road_address": road_address,
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                        }
                        new_auctions.append(auction)

                    # ✅ 기존 매물 업데이트
                    else:
                        if failed_count != int(
                            existing_item.get("failed_auction_count", 0)
                        ):
                            updated_auctions.append(
                                {
                                    "id": existing_item["id"],
                                    "minimum_price": item["notifyMinmaePrice1"],
                                    "status": status,
                                    "failed_auction_count": failed_count,
                                    "updated_at": datetime.now().isoformat(),
                                }
                            )

            except Exception as e:
                print(f"❗ 크롤링 중 오류: {e}")

        print(
            f"✅ 신규 {len(new_auctions)}건, 업데이트 {len(updated_auctions)}건 감지됨"
        )
        return raw_results, new_auctions, updated_auctions
