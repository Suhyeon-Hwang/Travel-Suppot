import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwrightimport os
import streamlit as st

# 서버 실행 시 처음에 한 번만 브라우저 설치 (가장 윗부분에 추가)
if "playwright_installed" not in st.session_state:
    os.system("playwright install chromium")
    st.session_state["playwright_installed"] = True

st.set_page_config(page_title="AI Family Travel Planner", layout="wide")

# 공항 코드 및 검색용 키워드 매핑
DEST_INFO = {
    "베트남 다낭": {"code": "dad", "city": "Danang"},
    "일본 후쿠오카": {"code": "fuk", "city": "Fukuoka"},
    "일본 오사카": {"code": "kix", "city": "Osaka"},
    "태국 방콕": {"code": "bkk", "city": "Bangkok"},
    "필리핀 보홀": {"code": "tag", "city": "Panglao"},
    "베트남 나트랑": {"code": "cxr", "city": "Nha+Trang"}
}

def fetch_flight_data(dest_name, start_date, end_date, adults, status):
    code = DEST_INFO[dest_name]["code"]
    # 날짜 포맷 변경 (YYMMDD)
    d_str = start_date.strftime("%y%m%d")
    r_str = end_date.strftime("%y%m%d")
    
    url = f"https://www.skyscanner.co.kr/transport/flights/sela/{code}/{d_str}/{r_str}/?adults={adults}"
    
    # 실제 크롤링 로직 (v4.0과 동일, 여기서는 요약)
    # ... (생략된 Playwright 로직) ...
    price_manwon = 35 # 임시값 (실제 연동 시 추출된 값 반환)
    return {"price": price_manwon, "link": url}

def fetch_hotel_data(dest_name, start_date, end_date, status):
    city = DEST_INFO[dest_name]["city"]
    check_in = start_date.strftime("%Y-%m-%d")
    check_out = end_date.strftime("%Y-%m-%d")
    
    # Trip.com 스타일의 검색 링크 생성
    trip_url = f"https://kr.trip.com/hotels/list?city={city}&checkIn={check_in}&checkOut={check_out}"
    
    return {"price_per_night": 12, "link": trip_url}

# --- UI 구성 ---
st.title("✈️ AI 가족 여행 예산 플래너 v5.0")
st.info("설정한 예산과 날짜에 맞춰 에이전트가 최적의 목적지를 선별합니다.")

with st.sidebar:
    st.header("📍 여행 조건")
    budget_per_person = st.number_input("1인당 예산 (만원)", value=100)
    family_size = st.slider("가족 인원", 1, 6, 4)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("출발일", datetime.now() + timedelta(days=30))
    with col2:
        nights = st.number_input("박수 (박)", min_value=1, value=3)
    
    end_date = start_date + timedelta(days=nights)
    st.write(f"📅 귀국일: {end_date}")
    
    search_btn = st.button("🚀 예산 내 목적지 찾기", use_container_width=True)

if search_btn:
    total_limit = budget_per_person * family_size
    st.subheader(f"🔍 총 {total_limit}만원으로 갈 수 있는 추천 여행지")
    
    results = []
    with st.status("에이전트가 전 세계 데이터를 분석 중...", expanded=True) as status:
        for dest in DEST_INFO.keys():
            st.write(f"🧐 {dest} 분석 중...")
            
            flight = fetch_flight_data(dest, start_date, end_date, family_size, status)
            hotel = fetch_hotel_data(dest, start_date, end_date, status)
            
            f_total = flight["price"] * family_size
            h_total = hotel["price_per_night"] * nights * (family_size // 2) # 2인 1실 기준
            grand_total = f_total + h_total
            
            # 예산 내에 들어오는 것만 리스트업하거나 상태 표시
            if grand_total <= total_limit:
                results.append({
                    "목적지": dest,
                    "항공권(인당)": f"{flight['price']}만원",
                    "숙소(총 {0}박)".format(nights): f"{h_total}만원",
                    "총 경비": f"{grand_total}만원",
                    "남는 예산": f"{total_limit - grand_total}만원",
                    "✈️ 항공권": flight["link"],
                    "🏨 숙소(Trip.com)": hotel["link"]
                })
        
        status.update(label="분석 완료!", state="complete", expanded=False)

    if results:
        st.data_editor(
            pd.DataFrame(results),
            column_config={
                "✈️ 항공권": st.column_config.LinkColumn("예약", display_text="이동"),
                "🏨 숙소(Trip.com)": st.column_config.LinkColumn("예약", display_text="이동")
            },
            hide_index=True, use_container_width=True
        )
    else:
        st.warning("선택한 예산 내에서 가능한 여행지가 없습니다. 예산을 늘리거나 날짜를 조정해 보세요.")
