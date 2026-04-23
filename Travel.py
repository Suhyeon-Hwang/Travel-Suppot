import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v23.0", layout="wide")

# 목적지 정보
DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

# 💡 [신규] 도시별 1박 평균 숙박비 (가성비 기준, 단위: 만원, 가족 전체 사용 방 1개 기준)
AVG_HOTEL_PRICE = {
    "베트남 다낭": 8, "일본 후쿠오카": 15, "일본 오사카": 18,
    "태국 방콕": 10, "필리핀 보홀": 12, "베트남 나트랑": 9
}

# (비행기 가격 가져오는 함수는 완벽하니까 그대로 유지!)
def fetch_flights_booking_v22(dest_code, start_date, end_date, adults):
    url = f"https://{HOST}/api/v1/flights/searchFlights"
    querystring = {
        "fromId": "ICN.AIRPORT", "toId": f"{dest_code}.AIRPORT",
        "departDate": start_date.strftime("%Y-%m-%d"), "returnDate": end_date.strftime("%Y-%m-%d"),
        "itineraryType": "ROUND_TRIP", "adults": str(adults), "children": "0",
        "currencyCode": "KRW", "cabinClass": "ECONOMY", "sortOrder": "BEST"
    }
    headers = {"x-rapidapi-key": RAPID_API_KEY, "x-rapidapi-host": HOST}

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        price_raw = 0
        
        if data.get("status") is True:
            flight_data = data.get("data", {})
            if isinstance(flight_data, dict):
                aggregation = flight_data.get("aggregation", {})
                min_price_info = aggregation.get("minPricePerAdult", {}) or aggregation.get("minPrice", {})
                
                if min_price_info:
                    units = min_price_info.get("units", 0)
                    currency = min_price_info.get("currencyCode", "USD")
                    price_raw = units * 1400 if currency == "USD" else units

        if price_raw > 0:
            return {"price": int(price_raw / 10000), "link": f"https://www.booking.com/flights/index.ko.html", "status": "SUCCESS"}
        return {"price": 0, "status": "NO_PRICE"}
    except Exception as e:
        return {"price": 0, "status": "ERROR"}

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 플래너 v23.0")
st.caption("항공권 실시간 연동 및 스마트 숙소 예산 시스템 탑재")

with st.sidebar:
    st.header("⚙️ 예산 및 인원")
    budget_limit = st.number_input("1인당 총 예산 (만원)", value=100)
    family_size = st.slider("가족 인원", 1, 6, 4)
    
    st.markdown("---")
    st.header("📅 일정 및 숙소")
    start_date = st.date_input("출발일", datetime.now() + timedelta(days=30))
    nights = st.number_input("여행 기간 (박)", value=3)
    
    # 💡 [신규] 숙소 등급 선택 UI
    hotel_tier = st.selectbox(
        "숙소 등급을 선택해 줘", 
        ["가성비 (3성급, 깔끔한 비즈니스)", "스탠다드 (4성급, 수영장/조식)", "럭셔리 (5성급, 풀빌라/호캉스)"]
    )
    
    # 등급에 따른 가격 배수 설정
    tier_multiplier = 1.0
    if "스탠다드" in hotel_tier: tier_multiplier = 1.5
    elif "럭셔리" in hotel_tier: tier_multiplier = 3.0

    st.markdown("---")
    search_btn = st.button("🚀 탐색 시작", use_container_width=True)

if search_btn:
    total_budget = budget_limit * family_size
    results = []
    
    with st.status("항공권 및 숙박 데이터를 융합하는 중...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 데이터 분석 중...")
            res = fetch_flights_booking_v22(code, start_date, start_date + timedelta(days=nights), family_size)
            
            if res["status"] == "SUCCESS":
                f_price_per_person = res['price']
                total_flight_price = f_price_per_person * family_size
                
                # 💡 [신규] 숙박비 계산 (도시별 기본가 * 등급 배수 * 숙박 일수)
                # 방 1~2개를 빌린다는 가정하에 가족 전체의 1박 요금으로 계산
                base_hotel_price = AVG_HOTEL_PRICE[name]
                total_hotel_price = int(base_hotel_price * tier_multiplier * nights)
                
                # 총 경비 = 항공권 총액 + 숙박비 총액
                grand_total = total_flight_price + total_hotel_price
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name,
                        "1인 항공권": f"{f_price_per_person}만원",
                        "가족 총 숙박비": f"{total_hotel_price}만원",
                        "총 경비(예상)": f"{grand_total}만원",
                        "남는 예산": f"{total_budget - grand_total}만원",
                        "예약 링크": res['link']
                    })

        status.update(label="분석 완료!", state="complete", expanded=False)

    if results:
        st.balloons()
        st.success(f"선택한 '{hotel_tier}' 기준으로 갈 수 있는 여행지야!")
        st.data_editor(
            pd.DataFrame(results),
            column_config={"예약 링크": st.column_config.LinkColumn("항공권 확인")},
            hide_index=True, use_container_width=True
        )
    else:
        st.error(f"😭 '{hotel_tier}' 기준으로는 예산을 초과해. 예산을 올리거나 숙소 등급을 낮춰봐!")
