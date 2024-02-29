import requests
import json
import pandas as pd
import folium

# csv파일 불러오기
csv = pd.read_csv('address.csv')
print(csv)

# 데이터프레임 주소값 추출
address = csv['주소']
print(address)

# 카카오맵 API 요청 및 지오코딩 함수 임포트
def get_location(address):
    url = 'https://dapi.kakao.com/v2/local/search/address.json?query=' + address
    # 'KaKaoAK '는 그대로 두고 개인키만 지우고 입력
    headers = {"Authorization": "KakaoAK df71b417860af8f3e49dc377c8a00efe"}

    try:
        api_json = json.loads(requests.get(url, headers=headers).text)
        address_data = api_json['documents'][0]['address']
        lat, lng = address_data['y'], address_data['x']
        return lat, lng

    except (KeyError, IndexError):
        # print(f"Error: Unable to retrieve coordinates for address - {address}")
        return None, None

latitude = []
longitude = []
error_addresses = []

for i in address:
    lat, lng = get_location(i)
    if lat is not None and lng is not None:
        print(f"Latitude: {lat}, Longitude: {lng}")
        latitude.append(lat)
        longitude.append(lng)

    else:
        latitude.append(lat)
        longitude.append(lng)
        error_addresses.append(i)

# 'DCU ID' 값에서 뒷 부분 '53'을 제거
csv['DCU ID'] = csv['DCU ID'].astype(str).str[:-2]

# Dataframe 만들기
address_df = pd.DataFrame({'DCU ID': csv['DCU ID'], '상세주소': csv['주소'], '위도': latitude, '경도': longitude})

# Dataframe 저장
address_df.to_csv('address1.csv')

# 에러가 발생한 주소 출력
if error_addresses:
    print("\n에러가 발생한 주소들:")
    for error_address in error_addresses:
        print(error_address)
print("\n에러가 발생한 주소 수:", len(error_addresses))

# Folium 지도 생성
m = folium.Map(location=[36.5, 127.5], zoom_start=9)  # 대한민국 중심 좌표 및 확대 수준 설정

# 각 주소에 Marker 추가
for i in range(len(address)):
    if latitude[i] is not None and longitude[i] is not None:
        folium.Marker(location=[latitude[i], longitude[i]], popup=str(csv['DCU ID'][i])).add_to(m)

# 지도 저장
m.save('map.html')
