import requests
import csv
import os
import re
import asyncio
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote
from telegram_bot import TelegramNotifier

# 로컬 개발환경에서만 .env 파일을 로드
if os.path.exists('.env'):
    load_dotenv()

async def main():
    telegramNotifier = TelegramNotifier(os.getenv('TELEGRAM_BOT_API_KEY'), os.getenv('TELEGRAM_CHAT_ID'))

    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)

    # 감시할 시군구 코드 세트
    detect_target = [
        {
            "sido_code" : "26",
            "sigu_code" : "350"
        }
    ]

    # 오늘 날짜와 14일 후 날짜 계산
    today = datetime.now()
    start_date = today - timedelta(days=14)
    end_date = today + timedelta(days=28)

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

    today_iso =  today.isoformat()
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    for target in detect_target:
        exist_datas = fetch_data_by_date_range("auctions", start_iso, today_iso)

        # 날짜를 'YYYY.MM.DD' 형식의 문자열로 변환
        start_date_str = today.strftime('%Y.%m.%d')
        end_date_str = end_date.strftime('%Y.%m.%d')

        # 1. URL 설정
        url = "https://www.courtauction.go.kr/RetrieveRealEstMulDetailList.laf"
        params = {
            "daepyoSidoCd": target["sido_code"],
            "daepyoSiguCd" : target["sigu_code"],
            "termStartDt": start_date_str,  # 동적으로 오늘 날짜 설정
            "termEndDt": end_date_str,      # 동적으로 14일 후 날짜 설정
            # "lclsUtilCd" : "0000802", #건물
            # "mclsUtilCd" : "000080201", #주거용건물
            "sclsUtilCd" : "00008020104", #아파트
            "srnID": "PNO102001",
            "page" : "default40",
            "targetRow" : "1"
        }

        # 2. GET 요청 보내기
        response = requests.get(url, params=params)
        response.encoding = 'euc-kr'  # 한글 인코딩 문제를 해결하기 위해 설정
        html = response.text

        # 3. BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(html, "html.parser")

        auction_data = []
        update_auction_data = [] # 업데이트 할 데이터
        # 4. 테이블 선택 (테이블 DOM 구조에 따라 id, class, 태그 등을 조정)
        table = soup.find("table")  # 테이블 태그를 찾음
        rows = table.find_all("tr")  # 테이블의 모든 행을 가져옴

        def extract_failed_auction_count(text):
            # 정규 표현식으로 '유찰'과 1자리 숫자 감지
            match = re.search(r'(유찰)\s*(\d)', text)
            
            if match:
                # 유찰과 숫자를 찾았다면, 유찰과 숫자를 반환
                return match.group(1), int(match.group(2))
            else:
                # 유찰이 없다면, 원본 텍스트를 그대로 반환
                return text, 0
        
        # 썸네일이 아닌 고화질 이미지로 변경
        def extract_original_image_url(thumbnail_url: str) -> str:
            # URL을 '&'로 나누기
            url_parts = thumbnail_url.split('&')
            
            # 'filename' 파트를 찾아서 수정
            for i, part in enumerate(url_parts):
                if 'filename=' in part:
                    filename_part = part.split('=')
                    filename = filename_part[1]
                    
                    # 'T_'가 있을 경우에만 제거
                    if filename.startswith('T_'):
                        filename = filename[2:]  # 'T_'를 제거
                        
                    url_parts[i] = f"filename={filename}"
            
            # 수정된 URL을 다시 합치기
            return 'https://www.courtauction.go.kr/' + '&'.join(url_parts)

        #사건 번호로 대표 이미지 추출
        def extract_image_url(case_id: str, jiwon_name : str) -> str:
            numbers = re.match(r"(\d+)타경(\d+)", case_id)
            if numbers:
                year, case_number = numbers.groups()
                slice = 10 - len(str(case_number))
                ganerated_case_number = str(year)+"0130000"[:slice] + str(case_number)
                # "jiwonNm"을 EUC-KR로 URL 인코딩
                encoded_jiwon_nm = quote(jiwon_name, encoding='euc-kr')
                url = f"https://www.courtauction.go.kr/RetrieveRealEstCarHvyMachineMulDetailInfo.laf?jiwonNm={encoded_jiwon_nm}"
                params = {
                    "saNo": ganerated_case_number,
                }
                response = requests.get(url, params=params)
                response.encoding = 'euc-kr'  # 한글 인코딩 문제를 해결하기 위해 설정
                html = response.text
                soup_inside = BeautifulSoup(html, "html.parser")
                # 테이블 선택 (테이블 DOM 구조에 따라 id, class, 태그 등을 조정)
                table = soup_inside.find_all("table", class_="Ltbl_dt")  # 테이블 태그를 찾음
                if len(table) > 0:
                    img_table = table[2]
                    img_alts = ["감정평가서, 관련사진", "감정평가서, 전경도", "현황조사, 전경도"]
                    for img_alt in img_alts:
                        img = img_table.find("img", alt=img_alt)
                        if img:
                            print(img_alt, img)
                            print(extract_original_image_url(img["src"]))
                            return extract_original_image_url(img["src"])

        def is_failed_auction_count_equal(exist_data, auction_status : str, failed_auction_count : int) -> bool:
            if exist_data["status"] != auction_status :
                return False
            elif exist_data["status"] == "유찰":
                if exist_data["failed_auction_count"] == failed_auction_count:
                    return True
                else:
                    return False
            else:
                return True
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

        if table:
            rows = table.find_all("tr")[1:]  # 헤더 제외
            if rows:
                print("\n=== 첫 번째 행의 셀 데이터 분석 ===")
                first_row = rows[0]
                cells = first_row.find_all("td")
                for idx, cell in enumerate(cells):
                    # 셀 내의 모든 텍스트 추출
                    texts = [text for text in cell.stripped_strings]
                    
                    # 원본 HTML도 함께 출력
                    # print(f"\n인덱스 {idx}:")
                    # print(f"텍스트 데이터: {texts}")
                    # print(f"원본 HTML: {cell}")
                    # print("-" * 50)
            for row in rows:
                cells = row.find_all("td")
                
                if cells:  # 빈 행 제외
                    case_cell = cells[1]  # 법원/사건번호가 있는 셀
                    case_info = [text for text in case_cell.stripped_strings]
                    case_id = case_info[1] #사건번호 추출
                    
                    apt_cell = cells[2]  # 아파트 분류
                    apt_info = [text for text in apt_cell.stripped_strings]

                    address_cell = cells[3]  # 주소 셀
                    address_info = [text for text in address_cell.stripped_strings]
                    area = re.search(r'\d+\.?\d*', address_info[1]) #주소 셀에서 면적 추출
                    if area:
                        area = area.group()

                    etc_cell = cells[4]  # 주소 셀
                    etc_info = [text for text in etc_cell.stripped_strings]

                    price_cell = cells[5]  # 가격 셀
                    # 첫 번째 가격 (tbl_btm_noline div에서)
                    estimated_price_div = price_cell.find('div', class_='tbl_btm_noline')
                    estimated_price = estimated_price_div.get_text(strip=True) if estimated_price_div else None
                    
                    # 두 번째 가격 (tbl_btm_line div에서)
                    minimum_price_div = price_cell.find('div', class_='tbl_btm_line')
                    minimum_price = minimum_price_div.get_text(strip=True).split('(')[0].strip() if minimum_price_div else None
                    
                    # 쉼표 제거하고 정수로 변환
                    if estimated_price:
                        estimated_price = int(estimated_price.replace(',', ''))
                    if minimum_price:
                        minimum_price = int(minimum_price.replace(',', ''))

                    auction_date_cell = cells[6]  # 매각기일 및 진행상태 셀
                    auction_date_info = [text for text in auction_date_cell.stripped_strings]

                    status, failed_auction_count = extract_failed_auction_count(auction_date_info[2])

                    

                    # 중복 데이터 확인
                    is_exist, match_data = compare_case_id_duplicated(exist_datas, case_id)
                    if is_exist:
                        # 이미 존재하는 데이터일 경우
                        is_equal = is_failed_auction_count_equal(match_data, status, failed_auction_count)
                        if is_equal:
                            # 완전히 동일한 데이터
                            # print(f"이미 존재하는 데이터: {case_id} {match_data['status']} {match_data['failed_auction_count']} {status} {failed_auction_count}")
                            continue
                        else:
                            # 데이터가 존재하지만 상태가 다른 경우
                            auction_info = {
                                'id' : match_data['id'],
                                'minimum_price' : minimum_price,
                                'status' : status,
                                'failed_auction_count' : failed_auction_count,
                                'updated_at': datetime.now().isoformat(),
                            }
                            update_auction_data.append(auction_info)
                            # print("존재하는 데이터지만 상태가 다름")
                    else:
                        # 신규 데이터 일 경우
                        # 이미지 URL 추출
                        img_src = extract_image_url(case_info[1], case_info[0])
                        if img_src:
                            auction_info = {
                                'court': case_info[0] if len(case_info) > 0 else None,
                                'case_id': case_info[1] if len(case_info) > 1 else None,
                                'category' : apt_info[1] if len(apt_info) > 1 else None,
                                'address' : address_info[0] if len(address_info) > 1 else None,
                                'area' : area,
                                'estimated_price' : estimated_price,
                                'minimum_price' : minimum_price,
                                'etc' : etc_info if len(etc_info) > 1 else None,
                                'status' : status,
                                'failed_auction_count' : failed_auction_count,
                                'auction_date' : auction_date_info[1],
                                'sido_code' : target["sido_code"],
                                'sigu_code' : target["sigu_code"],
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat(),
                                'thumbnail_src' : img_src
                            }
                            auction_data.append(auction_info)
                            await telegramNotifier.send_photo(img_src, f"*[신규 매물]*\n종류 : {apt_info[1]}\n주소 : {address_info[0]}\n면적 : {area}㎡\n감정가 : {int(estimated_price/10000):,} 만원\n최저 낙찰가 : {int(minimum_price/10000):,} 만원 \n상태 : {status} {f"{failed_auction_count}회" if failed_auction_count else ''}\n매각기일 : {auction_date_info[1]}")
                        else:
                            print("리스트에는 있으나 공고중인 물건은 아님(이미지 없음)")
            
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
