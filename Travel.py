import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "kiwi-com-cheap-flights.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v11.0", layout="wide")

DEST_INFO = {
    "베트남 다낭": "Danang", "일본 후쿠오카": "Fukuoka", "일본 오사카": "Osaka",
    "태국 방콕": "Bangkok", "필리핀 보홀": "Panglao", "베트남 나트랑": "Nha Trang"
}

def fetch_flights_rapid(dest_city, start_date, end_date, adults):
    url = f"https://{HOST}/round-trip"
    querystring = {
        "source": "ICN",  # 💡 "Seoul" 대신 공항 코드로 변경
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
            
            # 💡 [디버깅] 데이터가 안 나오면 이 데이터를 분석해야 함
            price_raw = 0
            
            # API 구조에 따른 유연한 파싱
            # 경로 1: itineraries -> buckets -> items
            itineraries = data.get('itineraries', {})
            buckets = itineraries.get('buckets', [])
            if not buckets and isinstance(data, list): # 만약 리스트로 온다면
                buckets = data
                
            if buckets:
                items = buckets[0].get('items', [])
                if items:
                    price_info = items[0].get('price', {})
                    price_raw = price_info.get('raw') or price_info.get('amount', 0)
            
            # 경로 2: 만약 경로 1이 실패하면 직접 price 찾기 (보험)
            if price_raw == 0 and isinstance(data, list) and len(data) > 0:
                price_raw = data[0].get('price', 0)

            if price_raw > 0:
                return {
                    "price": int(price_raw / 10000), 
                    "link": f"https://www.kiwi.com/ko/search/results/icn/{dest_city.lower()}",
                    "raw_data": None # 성공 시 데이터 숨김
                }
            return {"price": 0, "raw_data": data} # 실패 시 데이터 반환
    except Exception as e:
        return {"price": 0, "error": str(e)}
    return None

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 예산 플래너 v11.0")
st.caption("RapidAPI 실시간 연동 및 디버깅 모드 탑재")

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
    debug_data = {}
    
    with st.status("실시간 항공 데이터 수집 중...", expanded=True) as status:
        for name, city in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 조회 중...")
            res = fetch_flights_rapid(city, start_date, start_date + timedelta(days=nights), family_size)
            
            if res and res["price"] > 0:
                f_price = res['price']
                h_price_total = (nights * 6) * family_size 
                grand_total = (f_price * family_size) + h_price_total
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name, "항공권(인당)": f"{f_price}만원",
                        "총 경비(예상)": f"{grand_total}만원", "예약": res['link']
                    })
            elif res and "raw_data" in res:
                debug_data[name] = res["raw_data"]
                
        status.update(label="탐색 완료!", state="complete", expanded=False)

    if results:
        st.data_editor(pd.DataFrame(results), column_config={"예약": st.column_config.LinkColumn("이동")}, hide_index=True, use_container_width=True)
    else:
        st.error("❌ 예산 내 결과가 없습니다. (API 응답 구조 확인 필요)")
        with st.expander("🛠️ 개발자용 디버깅 데이터 보기"):
            st.write("API에서 받은 원본 데이터입니다. 이 내용을 나에게 보여주면 바로 고쳐줄게!")
            st.json(debug_data)
