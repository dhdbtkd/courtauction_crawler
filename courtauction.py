import requests
import os
import re
import asyncio
import base64
import socket
from pprint import pprint
from dotenv import load_dotenv
from datetime import datetime, timedelta
from supabase import create_client, Client
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote, unquote, urlencode
from telegram_bot import TelegramNotifier
from slack_sdk.web.async_client import AsyncWebClient

# 모니터링 할 타겟 시,구 불러오기
from monitoring_target import monitoring_targets

def is_oracle_instance():
    # 예: 호스트 이름 기반 구분
    hostname = socket.gethostname()
    print(f"hostname : {hostname}\nhostname : {hostname}\nhostname : {hostname}")
    if "instance" in hostname:  # 오라클 인스턴스의 고유 특징 포함
        print("it's oracle instance !!!!!!!!!!!\nit's oracle instance !!!!!!!!!!!\nit's oracle instance !!!!!!!!!!!")
        return True
    return False

def convert_yyyymmdd_to_dotted(date_str: str) -> str:
    return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"

# 로컬 개발환경에서만 .env 파일을 로드
if is_oracle_instance():
    load_dotenv('/home/ubuntu/scripts/.env')
else:
    if os.path.exists('.env'):
        load_dotenv()


async def main():
    telegramNotifier = TelegramNotifier(os.getenv('TELEGRAM_BOT_API_KEY'), os.getenv('TELEGRAM_CHAT_ID'))

    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)

    slack_token: str = os.getenv("SLACK_TOKEN")
    slack_client = AsyncWebClient(token=slack_token)
    await slack_client.chat_postMessage(
        channel="C089SGJ1SG3",
        text='cron 시작',
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"크론 시작!"
                }
            }
        ]
    )
    
    # 감시할 시군구 코드 세트
    detect_target = [
        {
            "sido_code" : "26",
            "sigu_code" : "350"
        }
    ]

    # 오늘 날짜와 14일 후 날짜 계산
    today = datetime.now()
    start_date = today - timedelta(days=15)
    end_date = today + timedelta(days=15)
    #기존 데이터 불러와야함
    def fetch_data_by_date_range(table_name: str, start_date: str, end_date: str):
        """
        Supabase에서 특정 날짜 범위의 데이터를 쿼리하는 함수
        :param table_name: 테이블 이름
        :param start_date: 시작 날짜 (ISO 8601 포맷)
        :param end_date: 종료 날짜 (ISO 8601 포맷)
        :return: 조회된 데이터 목록
        """
        try:
            response = supabase.table(table_name).select("*") \
                .gte("created_at", start_date) \
                .lte("created_at", end_date).execute()
            return response.data
        except Exception as e:
            print(f"Exception occurred: {e}")
            return []

    def compare_case_id_duplicated(data: List[Dict], case_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        사건번호가 중복되는 데이터가 있는지 확인하는 함수
        :param data: 리스트 형태의 데이터
        :param case_id: 사건번호
        :return: 중복되는 데이터가 있으면 True, 없으면 False
        """
        for item in data:
            if item['case_id'] == case_id:
                return True, item
        return False, None

    def extract_image_list(case_id : str, court_code : str, sido_code:str, sigu_code:str)->str:
            url = f"https://www.courtauction.go.kr/pgj/pgj15B/selectAuctnCsSrchRslt.on"
            data = {
                "dma_srchGdsDtlSrch": {
                    "csNo": case_id, #사건번호
                    "cortOfcCd": court_code, #담당법원코드
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
                        "bidBgngYmd": "20250207",
                        "bidEndYmd": "20250221",
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
                        "menuNm": "물건상세검색"
                    }
                }
            }
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:  # 요청이 성공했는지 확인
                response_data = response.json()  # JSON 응답 파싱
                data = response_data.get('data', {})  # 'data' 키 가져오기 (없으면 빈 딕셔너리 반환)
                if len(data) != 0 and 'dma_result' in data and len(data['dma_result'].get('csPicLst', [])) > 0:
                    return data['dma_result']['csPicLst']
                else:
                    return False
            else:
                return False


    today_iso =  today.isoformat()
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    for target in detect_target:
        exist_datas = fetch_data_by_date_range("auctions", start_iso, today_iso)

        # 날짜를 'YYYY.MM.DD' 형식의 문자열로 변환
        start_date_str = today.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        print(start_date_str, end_date_str)

        # 1. URL 설정
        url = "https://www.courtauction.go.kr/pgj/pgjsearch/searchControllerMain.on"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.courtauction.go.kr/",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {
            "dma_pageInfo": {
                "pageNo": 1,
                "pageSize": 50,
                "bfPageNo": "",
                "startRowNo": "",
                "totalCnt": "",
                "totalYn": "Y",
                "groupTotalCount": ""
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
                "carMdlNm": ""
            }
        }

        response = requests.post(url, json=data, headers=headers)

        # JSON 응답 파싱
        if response.status_code == 200:  # 요청이 성공했는지 확인
            try:
                response_data = response.json()  # JSON 응답 파싱
                data = response_data.get('data', {})  # 'data' 키 가져오기 (없으면 빈 딕셔너리 반환)
                search_results = data.get('dlt_srchResult', [])  # dlt_srchResult 키 가져오기, 없으면 빈 리스트 반환

                auction_data = []
                update_auction_data = [] # 업데이트 할 데이터
                # 데이터 순회
                for item in search_results:
                    failed_auction_count = int(item['yuchalCnt'])
                    is_exist, match_data = compare_case_id_duplicated(exist_datas, item['srnSaNo']) #사건번호
                    status = '신건'
                    if is_exist:
                        # 이미 존재하는 데이터일 경우
                        if failed_auction_count == int(match_data['failed_auction_count']):
                            # 완전히 동일한 데이터
                            print(f"이미 존재하는 데이터: {item['srnSaNo']} {match_data['status']} {match_data['failed_auction_count']} {status} {failed_auction_count}")
                            continue
                        else:
                            if failed_auction_count > 0:
                                status = '유찰'
                            # 데이터가 존재하지만 상태가 다른 경우
                            auction_info = {
                                'id' : match_data['id'],
                                'minimum_price' : item['notifyMinmaePrice1'],
                                'status' : status,
                                'failed_auction_count' : failed_auction_count,
                                'updated_at': datetime.now().isoformat(),
                            }
                            update_auction_data.append(auction_info)
                            print("존재하는 데이터지만 상태가 다름")
                    else:
                        # 신규 데이터 일 경우
                        images = extract_image_list(item['srnSaNo'], item['boCd'], target["sido_code"], target["sigu_code"])
                        if len(images) == 0:
                            continue
                        # 'pageSeq'가 '1'인 첫 번째 항목 찾기
                        image = next((image for image in images if image['pageSeq'] == "1"), None)
                        if image is None:
                            continue
                        # base64 문자열을 바이트로 디코딩
                        image_data = base64.b64decode(images[0]['picFile'])

                        # 원하는 디렉토리 경로 지정
                        if is_oracle_instance():
                            save_directory = f"/var/www/images/auctions/{image['csNo']}"  # 오라클 인스턴스용 경로
                        else:
                            save_directory = f"./images/auctions/{image['csNo']}"  # 여기에 원하는 경로를 입력하세요

                        # 디렉토리가 존재하지 않으면 생성
                        os.makedirs(save_directory, exist_ok=True)

                        # 파일 경로 설정
                        file_path = os.path.join(save_directory, f"{image['cortAuctnPicSeq']}.jpg")
                        file_url = f"http://oracle.artchive.in/images/auctions/{image['csNo']}/{image['cortAuctnPicSeq']}.jpg"

                        # 파일로 저장
                        with open(file_path, "wb") as file:
                            file.write(image_data)
                        if True:
                            # 매각 기일 처리
                            # 문자열을 datetime 객체로 변환
                            auction_date = datetime.strptime(item['maeGiil'], '%Y%m%d')
                            # 원하는 형식으로 다시 문자열로 변환
                            auction_date = auction_date.strftime('%Y.%m.%d')

                            #면적 추출
                            area = re.search(r'(\d+\.\d+)', item['pjbBuldList'])
                            # 추출된 면적 값 출력
                            if area:
                                area = area.group(1)

                            auction_info = {
                                'court': item['jiwonNm'] if len(item['jiwonNm']) > 0 else None,
                                'case_id': item['srnSaNo'] if len(item['srnSaNo']) > 1 else None,
                                'category' : item['dspslUsgNm'] if len(item['dspslUsgNm']) > 1 else None,
                                'address' : item['printSt'] if len(item['printSt']) > 1 else None,
                                'area' : area,
                                'estimated_price' : item['gamevalAmt'],
                                'minimum_price' : item['notifyMinmaePrice1'],
                                'etc' : item['mulBigo'] if len(item['mulBigo']) > 1 else None,
                                'status' : status,
                                'failed_auction_count' : failed_auction_count,
                                'auction_date' : auction_date,
                                'sido_code' : target["sido_code"],
                                'sigu_code' : target["sigu_code"],
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat(),
                                'thumbnail_src' : file_url
                            }
                            auction_data.append(auction_info)
                            caption = f"*[신규 매물]*\n종류 : {item['dspslUsgNm']}\n주소 : {item['printSt']}\n면적 : {area}㎡\n감정가 : {int(item['gamevalAmt'])/10000:,} 만원\n최저 낙찰가 : {int(item['notifyMinmaePrice1'])/10000:,} 만원 \n상태 : {status} {f"{failed_auction_count}회" if failed_auction_count else ''}\n매각기일 : {auction_date}"
                            # 텔레그램 메시지 전송
                            # await telegramNotifier.send_photo(img_src, caption)
                            # 슬랙 메시지 전송
                            # 이미지를 업로드
                            # slack_image_response = requests.get(img_src)
                            # if slack_image_response.status_code == 200:
                                # 이미지를 임시 파일로 저장
                                # with open("temp_image.jpg", "wb") as f:
                                #     f.write(slack_image_response.content)
                                
                            # 파일 업로드 및 메시지 전송
                            # result = await slack_client.files_upload_v2(
                            #     channel="C08A2QP3QCD",
                            #     title="",
                            #     file=file_path,
                            #     initial_comment="",
                            # )

                            # file_url = result["file"]["url_private_download"]  # 업로드된 파일의 URL 추출
                                
                                # # 임시 파일 삭제
                                # os.remove("temp_image.jpg")

                                # auction_detail_url = generate_auction_detail_url(case_info[1], case_info[0])
                            await slack_client.chat_postMessage(
                                channel="C089V5CB51S",
                                text=caption,
                                blocks=[
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"새 매물을 발견했어요"
                                        }
                                    },
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"*종류*\n🏢{item['dspslUsgNm']}\n*주소*\n{item['printSt']}\n*면적 :* {area}㎡"
                                        },
                                        "accessory": {
                                            "type": "image",
                                            "image_url": file_url,
                                            "alt_text": item['printSt']
                                        }
                                    },
                                    {
                                        "type": "section",
                                        "fields": [
                                            {
                                                "type": "mrkdwn",
                                                "text": f"*감정가:*\n{int(item['gamevalAmt'])/10000:,} 만원"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": f"*최저 낙찰가:*\n{int(item['notifyMinmaePrice1'])/10000:,} 만원"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": f"*상태:*\n{status}"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": f"*매각기일:*\n{convert_yyyymmdd_to_dotted(item['maeGiil'])}"
                                            }
                                        ]
                                    },
                                    # {
                                    #     "type": "actions",
                                    #     "elements": [
                                    #         {
                                    #             "type": "button",
                                    #             "text": {
                                    #                 "type": "plain_text",
                                    #                 "text": "자세히"
                                    #             },
                                    #             "url": auction_detail_url
                                    #         }
                                    #     ]
                                    # }
                                ]
                            )
                        else:
                            print("리스트에는 있으나 공고중인 물건은 아님(이미지 없음)")
                    pprint(item['buldNm'])  # 각 항목 출력
            except ValueError:
                print("JSON 디코딩에 실패했습니다.")
        else:
            print(f"요청 실패: {response.status_code}")

        
        def insert_to_supabase(data: List[Dict]) -> None:
            try:
                # court_auctions 테이블에 데이터 삽입
                result = supabase.table('auctions').insert(data).execute()
                print(f"Successfully inserted {len(data)} records")
                return result
            except Exception as e:
                print(f"Error inserting data: {str(e)}")
                raise
        if auction_data:
            # Supabase에 데이터 저장
            insert_to_supabase(auction_data)
            print("Data successfully scraped and stored in Supabase")
        else:
            print("No data found to insert")
        
        if update_auction_data:
            # Supabase에 데이터 저장
            for data in update_auction_data:
                result = supabase.table('auctions').update(data).eq('id', data['id']).execute()
                print(f"Successfully updated {len(update_auction_data)} records")
asyncio.run(main())
