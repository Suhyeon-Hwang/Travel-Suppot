import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- API 설정 ---
RAPID_API_KEY = "82b6769fbdmshc41f07cd8a897a6p1d658ajsn0df8b9bab233"
HOST = "kiwi-com-cheap-flights.p.rapidapi.com"

st.set_page_config(page_title="Family Travel Planner v13.0", layout="wide")

DEST_INFO = {
    "베트남 다낭": "Danang", "일본 후쿠오카": "Fukuoka", "일본 오사카": "Osaka",
    "태국 방콕": "Bangkok", "필리핀 보홀": "Panglao", "베트남 나트랑": "Nha Trang"
}

def fetch_flights_rapid(dest_city, start_date, end_date, adults):
    url = f"https://{HOST}/round-trip"
    
    # 💡 [핵심 해결책] 문자열이 아닌 '리스트' 객체로 생성
    # requests 라이브러리가 이 리스트를 받으면 API 표준 배열 형식으로 변환해줘.
    bags_list = [0] * adults      # [0, 0, 0, 0]
    hand_bags_list = [1] * adults # [1, 1, 1, 1]
    
    querystring = {
        "source": "ICN",
        "destination": dest_city,
        "currency": "KRW",
        "adults": str(adults),
        "adultsHandBags": hand_bags_list, # 👈 리스트 그대로 전달
        "adultsHoldBags": bags_list,      # 👈 리스트 그대로 전달
        "cabinClass": "ECONOMY",
        "departureDate": start_date.strftime("%Y-%m-%d"),
        "returnDate": end_date.strftime("%Y-%m-%d")
    }
    
    # 만약 위 방식도 안 될 경우를 대비해, API 문서에 있었던 변수명도 예비로 추가 (Overkill)
    querystring["handbags"] = str(adults)
    querystring["holdbags"] = "0"

    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": HOST
    }

    try:
        # ⚠️ 파라미터 전달 방식을 더 명확히 하기 위해 params=querystring 사용
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            
            # API 응답이 에러 메시지를 포함하고 있는지 확인
            if isinstance(data, dict) and data.get("__typename") == "AppError":
                return {"price": 0, "raw_data": data}

            price_raw = 0
            # 데이터 추출 경로 최적화
            itineraries = data.get('itineraries', {})
            buckets = itineraries.get('buckets', [])
            
            if buckets:
                items = buckets[0].get('items', [])
                if items:
                    price_info = items[0].get('price', {})
                    price_raw = price_info.get('raw') or price_info.get('amount', 0)

            if price_raw > 0:
                return {
                    "price": int(price_raw / 10000), 
                    "link": f"https://www.kiwi.com/ko/search/results/icn/{dest_city.lower()}",
                    "raw_data": None
                }
            return {"price": 0, "raw_data": data}
    except Exception as e:
        return {"price": 0, "error": str(e)}
    return None

# --- UI (동일) ---
st.title("✈️ AI 가족 여행 예산 플래너 v13.0")
st.caption("API 파라미터 전송 방식 최적화 (Multi-value Parameter 적용)")

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
    
    with st.status("실시간 항공 데이터 수집 및 분석 중...", expanded=True) as status:
        for name, city in DEST_INFO.items():
            st.write(f"🔍 {name} 가격 데이터 요청 중...")
            res = fetch_flights_rapid(city, start_date, start_date + timedelta(days=nights), family_size)
            
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
                
        status.update(label="탐색 완료!", state="complete", expanded=False)

    if results:
        st.data_editor(pd.DataFrame(results), column_config={"예약": st.column_config.LinkColumn("이동")}, hide_index=True, use_container_width=True)
    else:
        st.error("😭 이번에도 결과가 없습니다. 디버깅 데이터를 확인해 주세요.")
        with st.expander("🛠️ 디버깅 데이터 확인"):
            st.json(debug_data)
