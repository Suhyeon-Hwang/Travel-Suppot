import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v21.0", layout="wide")

DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

def fetch_flights_booking_v21(dest_code, start_date, end_date, adults):
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
        
        # 💡 [방어력 1] JSON이 아닐 경우 튕김 방지
        try:
            data = response.json()
        except:
            return {"price": 0, "status": "ERROR", "error": "API가 JSON이 아닌 데이터를 반환함"}

        # 💡 [방어력 2] data가 문자열(str)로 왔을 때 '.get()' 에러 방지
        if not isinstance(data, dict):
            return {"price": 0, "status": "ERROR", "error": f"예상치 못한 데이터 형태: {str(data)[:100]}"}

        price_raw = 0
        
        if data.get("status") is True:
            # 💡 [방어력 3] 데이터 파싱을 더 안전하게
            flight_data = data.get("data")
            if isinstance(flight_data, dict):
                flights_list = flight_data.get("flights", [])
                if flights_list and isinstance(flights_list, list):
                    price_info = flights_list[0].get("price", {})
                    # amount, raw, total 중 걸리는 거 하나 가져오기
                    price_raw = price_info.get("amount") or price_info.get("raw") or price_info.get("total", 0)

        if price_raw > 0:
            return {
                "price": int(float(price_raw) / 10000), 
                "link": f"https://www.booking.com/flights/index.ko.html",
                "status": "SUCCESS"
            }
            
        # 💡 [방어력 4] 크롬 뻗음 방지! 데이터를 500자로 잘라서 보냄
        safe_raw = str(data)[:500] + "... (데이터가 너무 길어서 생략됨)"
        return {"price": 0, "status": "NO_PRICE", "raw_preview": safe_raw}
            
    except Exception as e:
        return {"price": 0, "status": "ERROR", "error": str(e)}

# --- UI 부분 ---
st.title("✈️ AI 여행 플래너 v21.0")
st.caption("크롬 프리징 방지 및 강철 파싱 로직 탑재")

with st.sidebar:
    st.header("⚙️ 검색 조건")
    budget_limit = st.number_input("1인당 예산 (만원)", value=100)
    family_size = st.slider("인원", 1, 6, 4)
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
            res = fetch_flights_booking_v21(code, start_date, start_date + timedelta(days=nights), family_size)
            
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
        st.data_editor(
            pd.DataFrame(results),
            column_config={"예약": st.column_config.LinkColumn("이동")},
            hide_index=True, use_container_width=True
        )
    else:
        st.error("😭 결과가 없습니다. (디버깅 데이터를 확인해 줘!)")
        with st.expander("🛠️ 요약된 API 응답 확인 (크롬 멈춤 방지)"):
            st.json(debug_box)
