import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v22.0", layout="wide")

DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

def fetch_flights_booking_v22(dest_code, start_date, end_date, adults):
    url = f"https://{HOST}/api/v1/flights/searchFlights"
    
    querystring = {
        "fromId": "ICN.AIRPORT",
        "toId": f"{dest_code}.AIRPORT",
        "departDate": start_date.strftime("%Y-%m-%d"),
        "returnDate": end_date.strftime("%Y-%m-%d"),
        "itineraryType": "ROUND_TRIP",
        "adults": str(adults),
        "children": "0",
        "currencyCode": "KRW",
        "cabinClass": "ECONOMY",
        "sortOrder": "BEST"
    }
    
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        
        try:
            data = response.json()
        except:
            return {"price": 0, "status": "ERROR", "error": "API 응답이 JSON이 아님"}

        if not isinstance(data, dict):
            return {"price": 0, "status": "ERROR", "error": "데이터 형태 오류"}

        price_raw = 0
        
        if data.get("status") is True:
            flight_data = data.get("data", {})
            if isinstance(flight_data, dict):
                # 💡 [핵심] 스크린샷에서 찾은 'aggregation -> minPricePerAdult' 경로 탐색
                aggregation = flight_data.get("aggregation", {})
                min_price_info = aggregation.get("minPricePerAdult", {}) or aggregation.get("minPrice", {})
                
                if min_price_info:
                    units = min_price_info.get("units", 0)
                    currency = min_price_info.get("currencyCode", "USD")
                    
                    # 💡 API가 달러(USD)로 줄 경우 대략적인 환율(1,400원) 적용
                    if currency == "USD":
                        price_raw = units * 1400
                    else:
                        price_raw = units # KRW일 경우 그대로 사용

        if price_raw > 0:
            return {
                "price": int(price_raw / 10000), # 만원 단위로 변환
                "link": f"https://www.booking.com/flights/index.ko.html",
                "status": "SUCCESS"
            }
            
        safe_raw = str(data)[:500] + "... (생략)"
        return {"price": 0, "status": "NO_PRICE", "raw_preview": safe_raw}
            
    except Exception as e:
        return {"price": 0, "status": "ERROR", "error": str(e)}

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 플래너 v22.0")
st.caption("JSON 파싱 완벽 적중 및 USD 자동 환전 기능 탑재")

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
    debug_box = {}
    
    with st.status("실시간 최저가 데이터를 수집 중...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 분석 중...")
            res = fetch_flights_booking_v22(code, start_date, start_date + timedelta(days=nights), family_size)
            
            if res["status"] == "SUCCESS":
                f_price = res['price']
                h_price_total = (nights * 6) * family_size 
                grand_total = (f_price * family_size) + h_price_total
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name,
                        "항공권(인당)": f"{f_price}만원",
                        "총 경비(예상)": f"{grand_total}만원",
                        "예약": res['link']
                    })
            else:
                debug_box[name] = res

        status.update(label="분석 완료!", state="complete", expanded=False)

    if results:
        st.balloons()
        st.success("드디어 가격표를 뜯어냈어! 추천 여행지 리스트야.")
        st.data_editor(
            pd.DataFrame(results),
            column_config={"예약": st.column_config.LinkColumn("항공권 예약")},
            hide_index=True, use_container_width=True
        )
    else:
        st.error("😭 예산 내 결과가 없습니다.")
        with st.expander("🛠️ 요약된 API 응답 확인"):
            st.json(debug_box)
