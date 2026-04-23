import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v20.0", layout="wide")

# 목적지 IATA 코드
DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

def fetch_flights_booking_v20(dest_code, start_date, end_date, adults):
    url = f"https://{HOST}/api/v1/flights/searchFlights"
    
    # 💡 [핵심] 테스트 콘솔에서 성공했던 파라미터 형식을 그대로 적용
    querystring = {
        "fromId": "ICN.AIRPORT",             # 출발지: 인천공항
        "toId": f"{dest_code}.AIRPORT",      # 목적지: DAD.AIRPORT 등
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
        data = response.json()
        
        # 200 OK는 떴으니 이제 가격만 잘 꺼내오면 돼!
        price_raw = 0
        
        # Booking.com API 응답 구조 정밀 탐색
        if data.get("status") is True:
            flights_list = data.get("data", {}).get("flights", [])
            if flights_list:
                # 첫 번째(Best/Cheapest) 결과의 가격 정보
                price_info = flights_list[0].get("price", {})
                price_raw = price_info.get("amount", 0)

        if price_raw > 0:
            return {
                "price": int(price_raw / 10000), 
                "link": f"https://www.booking.com/flights/index.ko.html",
                "status": "SUCCESS"
            }
        return {"price": 0, "status": "NO_PRICE", "raw": data}
            
    except Exception as e:
        return {"price": 0, "status": "ERROR", "error": str(e)}

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 플래너 v20.0")
st.caption("Booking.com API 검증 완료 및 실시간 연동 버전")

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
    
    with st.status("실시간 항공권 최저가를 수집하고 있어...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 분석 중...")
            res = fetch_flights_booking_v20(code, start_date, start_date + timedelta(days=nights), family_size)
            
            if res["status"] == "SUCCESS":
                f_price = res['price']
                # 숙박비는 1인 1박 6만원으로 우선 계산 (고도화 가능)
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
        st.balloons() # 성공 기념 풍선!
        st.data_editor(
            pd.DataFrame(results),
            column_config={"예약": st.column_config.LinkColumn("이동")},
            hide_index=True, use_container_width=True
        )
    else:
        st.error("😭 예산 내 결과가 없습니다. (데이터는 왔지만 가격 조건이 안 맞을 수 있어)")
        with st.expander("🛠️ API 응답 원본 확인"):
            st.json(debug_box)
