import requests
from config.settings import settings


def get_coordinates(address: str):
    """네이버 지도 API를 이용해 주소 → (경도, 위도) 조회"""
    if not address:
        return None, None

    try:
        url = f"https://maps.apigw.ntruss.com/map-geocode/v2/geocode?query={address}"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": settings.NAVER_ACCESS_KEY,
            "X-NCP-APIGW-API-KEY": settings.NAVER_CLIENT_SECRET,
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        addresses = data.get("addresses", [])
        if not addresses:
            return None, None

        x = addresses[0].get("x")  # 경도
        y = addresses[0].get("y")  # 위도
        jibun_address = addresses[0].get("jibunAddress")  # 위도
        road_address = addresses[0].get("roadAddress")  # 위도
        return x, y, jibun_address, road_address

    except Exception as e:
        print(f"❗ 네이버 지도 API 오류: {e}")
        return None, None
