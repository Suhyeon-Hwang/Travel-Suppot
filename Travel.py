import streamlit as st
import pandas as pd
import plotly.express as px
from pykrx import stock # KRX 공식 데이터 라이브러리
from datetime import datetime, timedelta

# --- 1. 실시간 주가 가져오기 (KRX 공식 데이터 버전) ---
@st.cache_data(ttl=300) # 5분간 캐시 유지 (서버 부하 및 차단 방지)
def get_realtime_price(code):
    try:
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")
        # 혹시 장 시작 전이거나 휴일일 수 있으니 최근 3일치 데이터를 조회
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
        
        # 종목의 가격 정보 가져오기
        df = stock.get_market_ohlcv_by_date(start_date, today, code)
        
        if not df.empty:
            # 가장 최근 날짜의 '종가' 가져오기
            price = df['종가'].iloc[-1]
            return int(price)
        else:
            # 데이터를 못 가져오면 0을 반환하기보다 에러 메시지 띄움
            return None
    except Exception as e:
        return None

# 종목 설정
TICKERS = {
    "SP500": "360200",      
    "DOW": "460320",        
    "GOLD": "411060",       
    "BOND": "430160"        
}

st.set_page_config(page_title="실시간 퇴직연금 리밸런싱", layout="wide")
st.title("🛡️ 무적의 퇴직연금(DC) 리밸런싱 시뮬레이터")

# --- 데이터 로딩 ---
with st.spinner('한국거래소에서 데이터를 안전하게 불러오는 중...'):
    prices = {name: get_realtime_price(code) for name, code in TICKERS.items()}

# 에러 체크
if None in prices.values():
    st.error("⚠️ 거래소 서버 응답이 지연되고 있습니다. 잠시 후 상단의 새로고침 버튼을 눌러주세요.")
    # 임시 방편: 에러가 나도 화면이 깨지지 않게 0원 처리
    prices = {k: (v if v is not None else 0) for k, v in prices.items()}

# --- UI 및 계산 로직 (기존과 동일) ---
st.sidebar.header("1. 보유 수량 입력")
qty_sp500 = st.sidebar.number_input("S&P500 (주)", value=803)
qty_dow = st.sidebar.number_input("배당다우존스 (주)", value=618)
qty_gold = st.sidebar.number_input("금현물 (주)", value=86)
qty_bond = st.sidebar.number_input("10년국채 (주)", value=1241)

# 평가금액 계산
val_sp500 = qty_sp500 * prices["SP500"]
val_dow = qty_dow * prices["DOW"]
val_gold = qty_gold * prices["GOLD"]
val_bond = qty_bond * prices["BOND"]

# ... (이후 시각화 코드는 기존과 동일하게 작성)
st.write(f"현재 반영된 주가: S&P500({prices['SP500']:,}원), 배당다우({prices['DOW']:,}원), 금({prices['GOLD']:,}원), 국채({prices['BOND']:,}원)")

current_risk = val_sp500 + val_dow + val_gold
current_safe = val_bond
current_total = current_risk + current_safe

# 신규 입금액 섹션
st.divider()
new_deposit = st.number_input("신규 입금액 (원)", value=1000000)
add_bond = st.slider("안전차산(국채)에 몰빵하기", 0, new_deposit, new_deposit)
add_risk = new_deposit - add_bond

# 결과 표시
new_total = current_total + new_deposit
new_risk_ratio = ((current_risk + add_risk) / new_total) * 100

st.metric("예상 위험자산 비중", f"{new_risk_ratio:.2f}%", delta=f"{new_risk_ratio-70:.2f}%", delta_color="inverse")
if new_risk_ratio > 70:
    st.warning("🚨 여전히 70%를 초과합니다! 국채 매수 비중을 더 늘리세요.")
else:
    st.success("✅ 목표 비율 달성 가능!")
