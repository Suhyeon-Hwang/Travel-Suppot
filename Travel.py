import streamlit as st
import pandas as pd
import requests
import base64
import json
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v18.0", layout="wide")

# 목적지 IATA 코드
DEST_INFO = {
    "베트남 다낭": "DAD", "일본 후쿠오카": "FUK", "일본 오사카": "KIX",
    "태국 방콕": "BKK", "필리핀 보홀": "TAG", "베트남 나트랑": "CXR"
}

# Booking.com API가 요구하는 형식으로 ID 인코딩하는 함수
def get_encoded_id(iata_code):
    obj = {"t": "skyscanner", "i": iata_code}
    json_str = json.dumps(obj)
    return base64.b64encode(json_str.encode()).decode()

def fetch_flights_booking(dest_code, start_date, end_date, adults):
    url = f"https://{HOST}/api/v1/flights/searchFlights"
    
    # 💡 [핵심] 에러 메시지에 맞춰 파라미터 이름과 값 전면 수정
    querystring = {
        "fromId": get_encoded_id("ICN"),      # ICN -> 전용 ID로 변환
        "toId": get_encoded_id(dest_code),    # 목적지 -> 전용 ID로 변환
        "departDate": start_date.strftime("%Y-%m-%d"), # fromDate가 아니라 departDate!
        "returnDate": end_date.strftime("%Y-%m-%d"), # toDate가 아니라 returnDate!
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
        
        # 성공 시 가격 추출 (Booking.com v15 구조)
        price_raw = 0
        flights_data = data.get('data', {}).get('flights', [])
        
        if flights_data:
            # 첫 번째 결과의 가격 정보 가져오기
            price_raw = flights_data[0].get('price', {}).get('amount', 0)

        if price_raw > 0:
            return {
                "price": int(price_raw / 10000), 
                "link": "https://www.booking.com/flights/",
                "status": "SUCCESS"
            }
        return {"price": 0, "status": "NO_DATA", "raw": data}
            
    except Exception as e:
        return {"price": 0, "status": "ERROR", "error": str(e)}

# --- UI 부분 ---
st.title("✈️ AI 가족 여행 플래너 v18.0")
st.caption("Booking.com API 정밀 파라미터 연동 버전")

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
    
    with st.status("Booking.com 공식 데이터를 정밀 분석 중...", expanded=True) as status:
        for name, code in DEST_INFO.items():
            st.write(f"🔍 {name} 항공권 조회 중...")
            res = fetch_flights_booking(code, start_date, start_date + timedelta(days=nights), family_size)
            
            if res["status"] == "SUCCESS":
                f_price = res['price']
                h_price_total = (nights * 6) * family_size 
                grand_total = (f_price * family_size) + h_price_total
                
                if (grand_total / family_size) <= budget_limit:
                    results.append({
                        "목적지": name, "항공권(인당)": f"{f_price}만원",
                        "총 경비": f"{grand_total}만원", "예약": res['link']
                    })
            else:
                debug_box[name] = res

        status.update(label="탐색 완료!", state="complete", expanded=False)

    if results:
        st.success(f"{len(results)}개의 추천 여행지를 찾았어!")
        st.data_editor(pd.DataFrame(results), column_config={"예약": st.column_config.LinkColumn("항공권")}, hide_index=True)
    else:
        st.error("😭 예산 내 결과가 없습니다.")
        with st.expander("🛠️ 정밀 디버깅 로그 확인"):
            st.json(debug_box)
