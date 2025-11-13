#대한항공에 api방식으로 접근시도했으나 failed 20250209

import requests
import httpx
import asyncio

# 1. URL 설정
url = "https://www.koreanair.com/api/rp/dx/search/air-bounds"

headers = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
"Referer": "https://www.koreanair.com",
"Content-Type": "application/json; charset=UTF-8",
"Accept": "application/json, text/javascript, */*; q=0.01",
"X-Requested-With": "XMLHttpRequest",
"ksessionid" : "7b0b89853e291a894860b21a8feea9f320250209W"
}
data = {
  "currencyCode": "KRW",
  "itineraries": [
    {
      "departureDateTime": "2025-02-13T00:00:00.000",
      "destinationLocationCode": "CJU",
      "originLocationCode": "PUS",
      "commercialFareFamilies": [
        "DOMEY2",
        "DOMEY1",
        "DOMPR1"
      ],
      "isRequestedBound": 'true'
    }
  ],
  "travelers": [
    {
      "passengerTypeCode": "ADT"
    }
  ],
  "searchPreferences": {
    "showSoldOut": 'true'
  }
}

async def main():
  # httpx 사용
  async with httpx.AsyncClient(http2=True) as client:
      response = await client.post(url, json=data, headers=headers)
      print(response)
      response_data = response.json()
      print(response_data)

asyncio.run(main())


# response = requests.post(url, json=data, headers=headers)
# print(response)
# response_data = response.json()
# print(response_data)