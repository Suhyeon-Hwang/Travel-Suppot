import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v25.1", layout="wide")

DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

AVG_HOTEL_PRICE = {
    "베트남 다낭": 8, "일본 후쿠오카": 15, "일본 오사카": 18,
    "태국 방콕": 10, "필리핀 보홀": 12, "베트남 나트랑": 9
}

def fetch_flights_booking_v25(dest_code, dest_name, start_date, end_date, adults):
    url = f"https://{HOST}/api/v1/flights/searchFlights"
    
    str_start = start_date.strftime('%Y-%m-%d')
    str_end = end_date.strftime('%Y-%m-%d')
    
    querystring = {
        "fromId": "ICN.AIRPORT",
        "toId": f"{dest_code}.AIRPORT",
        "departDate": str_start,
        "returnDate": str_end,
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
            return {"price": 0, "status": "ERROR"}

        if not isinstance(data, dict):
            return {"price": 0, "status": "ERROR"}

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
            flight_link = f"https://www.google.com/flights?hl=ko#flt=ICN.{dest_code}.{str_start}*{dest_code}.ICN.{str_end}"
            hotel_link = f"https://www.booking.com/searchresults.ko.html?ss={dest_name}&checkin={str_start}&checkout={str_end}&group_adults={adults}&no_rooms=1"
            
            return {
                "price": int(price_raw / 10000), 
                "flight_link": flight_link,
                "hotel_link": hotel_link,
                "status": "SUCCESS",
                "raw": data # 디버깅용으로 원본 데이터 추가
            }
            
        return {"price": 0, "status": "NO_PRICE", "raw": data}
            
    except Exception as e:
        return {"price": 0, "status": "ERROR", "error": str(e)}

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 플래너 v25.1")
st.caption("디버깅 모드 부활 버전 (API 한도 초과 검사)")

with st.sidebar:
    st.header("⚙️ 예산 및 인원")
    budget_limit = st.number_input("1인당 총 예산 (만원)", value=100)
    family_size = st.slider("가족 인원", 1, 6, 4)
    
    st.markdown("---")
    st.header("📅 일정 및 숙소")
    start_date = st.date_input("출발일", datetime.now() + timedelta(days=30))
    nights = st.number_input("여행 기간 (박)", value=3)
    
    hotel_tier = st.selectbox(
        "숙소 등급을 선택해 줘", 
        ["가성비 (3성급, 깔끔한 비즈니스)", "스탠다드 (4성급, 수영장/조식)", "럭셔리 (5성급, 풀빌라/호캉스)"]
    )
    
    tier_multiplier = 1.0
    if "스탠다드" in hotel_tier: tier_multiplier = 1.5
    elif "럭셔리" in hotel_tier: tier_multiplier = 3.0

    st.markdown("---")
    search_btn = st.button("🚀 탐색 시작", use_container_width=True)

if search_btn:
    total_budget = budget_limit * family_size
    results = []
    debug_box = {} # 에러 데이터를 담을 바구니
    
    with st.status("최적의 항공권과 숙소 예약 링크를 생성 중...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 데이터 분석 중...")
            res = fetch_flights_booking_v25(code, name, start_date, start_date + timedelta(days=nights), family_size)
            
            if res["status"] == "SUCCESS" and res['price'] > 0:
                f_price_per_person = res['price']
                total_flight_price = f_price_per_person * family_size
                
                base_hotel_price = AVG_HOTEL_PRICE[name]
                total_hotel_price = int(base_hotel_price * tier_multiplier * nights)
                grand_total = total_flight_price + total_hotel_price
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name,
                        "왕복 항공권(1인)": f"{f_price_per_person}만원",
                        "가족 총 숙박비": f"{total_hotel_price}만원",
                        "총 경비(예상)": f"{grand_total}만원",
                        "남는 예산": f"{total_budget - grand_total}만원",
                        "✈️ 항공권": res['flight_link'],
                        "🏨 숙소": res['hotel_link']
                    })
            else:
                # 에러가 나면 디버깅 박스에 저장
                debug_box[name] = res

        status.update(label="분석 완료!", state="complete", expanded=False)

    if results:
        st.balloons()
        st.success("표 오른쪽의 링크를 누르면 세팅된 조건으로 바로 예약 화면이 열려!")
        st.data_editor(
            pd.DataFrame(results),
            column_config={
                "✈️ 항공권": st.column_config.LinkColumn("구글 플라이트", display_text="최저가 보기"),
                "🏨 숙소": st.column_config.LinkColumn("Booking.com", display_text="리조트 찾기")
            },
            hide_index=True, use_container_width=True
        )
    else:
        st.error("😭 결과가 안 나왔어. (예산 문제가 아니라 API 에러일 확률이 높아!)")
        # 💡 지웠던 디버깅 창 부활!
        if debug_box:
            with st.expander("🛠️ 긴급 디버깅: API 에러 원인 보기"):
                st.write("아래 메시지 중에 `You have exceeded the MONTHLY quota` 같은 글자가 있는지 확인해 봐!")
                st.json(debug_box)
