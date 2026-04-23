import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 (화면에 보이는 값 그대로 넣어줘!) ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "kiwi-com-cheap-flights.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v9.0", layout="wide")

# 목적지 도시 이름 (이 API는 코드보다 도시 이름이 더 잘 먹힐 수 있어)
DEST_INFO = {
    "베트남 다낭": "Danang", 
    "일본 후쿠오카": "Fukuoka", 
    "일본 오사카": "Osaka",
    "태국 방콕": "Bangkok", 
    "필리핀 보홀": "Panglao", 
    "베트남 나트랑": "Nha Trang"
}

def fetch_flights_rapid(dest_city, start_date, end_date, adults):
    url = f"https://{HOST}/round-trip"
    querystring = {
        "source": "Seoul",
        "destination": dest_city,
        "currency": "KRW",
        "adults": str(adults),
        "cabinClass": "ECONOMY",
        "departureDate": start_date.strftime("%Y-%m-%d"),
        "returnDate": end_date.strftime("%Y-%m-%d")
    }
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            
            # 💡 [핵심] 스크린샷에서 확인된 'Itineraries' 구조에 맞춰 데이터 추출
            # 보통 이런 API는 buckets -> items 안에 진짜 가격이 들어있어.
            price_raw = 0
            
            # 1단계: itineraries 찾기
            itineraries = data.get('itineraries', {})
            # 2단계: buckets 안의 첫 번째 묶음 찾기
            buckets = itineraries.get('buckets', [])
            
            if buckets:
                # 3단계: 첫 번째 아이템의 가격 정보 가져오기
                items = buckets[0].get('items', [])
                if items:
                    # price -> raw (또는 amount) 경로 탐색
                    price_info = items[0].get('price', {})
                    price_raw = price_info.get('raw') or price_info.get('amount', 0)

            if price_raw > 0:
                return {
                    "price": int(price_raw / 10000), 
                    "link": f"https://www.kiwi.com/ko/search/results/seoul-south-korea/{dest_city.lower()}"
                }
            else:
                # 데이터는 왔는데 가격을 못 찾은 경우 디버깅용 로그
                print(f"[{dest_city}] 데이터를 받았으나 가격 파싱 실패")
    except Exception as e:
        print(f"API 통신 에러: {e}")
    return None

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 예산 플래너 V9.0 (RapidAPI 연동)")
st.caption("설정한 예산 내에서 실시간 항공권을 분석하여 최적의 목적지를 추천해.")

with st.sidebar:
    st.header("⚙️ 검색 조건")
    budget_limit = st.number_input("1인당 예산 (만원)", value=100)
    family_size = st.slider("가족 인원", 1, 6, 4)
    start_date = st.date_input("출발일", datetime.now() + timedelta(days=30))
    nights = st.number_input("여행 기간 (박)", value=3)
    search_btn = st.button("🚀 탐색 시작", use_container_width=True)

if search_btn:
    total_budget = budget_limit * family_size
    results = []
    
    with st.status("실시간 항공 데이터 수집 중...", expanded=True) as status:
        for name, city in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 조회 중...")
            data = fetch_flights_rapid(city, start_date, start_date + timedelta(days=nights), family_size)
            
            if data:
                f_price = data['price']
                # 숙박비 추정 (1인 1박 6만원 기준)
                h_price_total = (nights * 6) * family_size 
                grand_total = (f_price * family_size) + h_price_total
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name,
                        "항공권(인당)": f"{f_price}만원",
                        "총 경비(예상)": f"{grand_total}만원",
                        "남는 예산": f"{total_budget - grand_total}만원",
                        "✈️ 항공권 보기": data['link']
                    })
        status.update(label="탐색 완료!", state="complete", expanded=False)

    if results:
        st.data_editor(
            pd.DataFrame(results),
            column_config={
                "✈️ 항공권 보기": st.column_config.LinkColumn("예약", display_text="이동")
            },
            hide_index=True, use_container_width=True
        )
    else:
        st.warning("예산 내 결과가 없습니다. 조건을 조정해 보세요.")
