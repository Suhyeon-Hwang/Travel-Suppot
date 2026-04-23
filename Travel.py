import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 (Skyscanner44용으로 변경) ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "skyscanner44.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v14.0", layout="wide")

# 목적지 IATA 코드
DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

def fetch_flights_skyscanner(dest_code, start_date, end_date, adults):
    url = f"https://{HOST}/search-flights"
    querystring = {
        "departureDate": start_date.strftime("%Y-%m-%d"),
        "returnDate": end_date.strftime("%Y-%m-%d"),
        "destination": dest_code,
        "origin": "ICN",
        "adults": str(adults),
        "currency": "KRW",
        "cabinClass": "economy"
    }
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            
            # Skyscanner44 응답 구조 파싱
            # 보통 itineraries -> buckets -> items 순서임
            price_raw = 0
            itineraries = data.get('itineraries', {})
            buckets = itineraries.get('buckets', [])
            
            if buckets:
                items = buckets[0].get('items', [])
                if items:
                    price_raw = items[0].get('price', {}).get('raw', 0)

            if price_raw > 0:
                return {
                    "price": int(price_raw / 10000), 
                    "link": f"https://www.skyscanner.co.kr/transport/flights/icn/{dest_code}"
                }
            return {"price": 0, "raw_data": data}
    except Exception as e:
        return {"price": 0, "error": str(e)}
    return None

# --- UI 부분 (버전만 v14.0으로 변경) ---
st.title("✈️ AI 가족 여행 예산 플래너 v14.0")
st.caption("안정적인 Skyscanner44 API 엔진으로 전면 교체 완료!")

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
    
    with st.status("스카이스캐너 서버에서 데이터를 가져오는 중...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 분석 중...")
            res = fetch_flights_skyscanner(code, start_date, start_date + timedelta(days=nights), family_size)
            
            if res and res.get("price", 0) > 0:
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
                
        status.update(label="분석 완료!", state="complete", expanded=False)

    if results:
        st.data_editor(pd.DataFrame(results), column_config={"예약": st.column_config.LinkColumn("이동")}, hide_index=True, use_container_width=True)
    else:
        st.error("😭 예산 내 결과가 없습니다.")
        if debug_data:
            with st.expander("🛠️ API 원본 데이터 (응답 오류 확인용)"):
                st.json(debug_data)
