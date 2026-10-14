import re
import requests
import streamlit as st

st.set_page_config(page_title="비슬고 급식 알레르기 케어", page_icon="🏫")

MY_NEIS_KEY = '2706781616044e5bae5ed9590e87d93b'
ATPT_OFCDC_SC_CODE = 'D10'  # 대구광역시교육청 코드
SD_SCHUL_CODE = '7240453'     # 비슬고등학교 학교 코드

ALLERGY_MAP = {
    '1': '난류(달걀)',
    '2': '우유',
    '3': '메밀',
    '4': '땅콩',
    '5': '대두(콩)',
    '6': '밀',
    '7': '고등어',
    '8': '게',
    '9': '새우',
    '10': '돼지고기',
    '11': '복숭아',
    '12': '토마토',
    '13': '아황산류',
    '14': '호두',
    '15': '닭고기',
    '16': '쇠고기',
    '17': '오징어',
    '18': '조개류(굴/전복/홍합)',
    '19': '잣',
}

st.title('🏫 비슬고 맞춤형 급식 알레르기 케어 시스템')
st.caption('알레르기 반응 강도를 선택하면 개인 맞춤 식단 위험 점수와 교내 실전 식사 가이드를 제공합니다.')

from datetime import datetime, timedelta

# 오늘 날짜를 구하고 주말일 경우 가장 가까운 평일(금요일)로 자동 설정
today = datetime.now()
weekday = today.weekday()  # 월:0 ~ 일:6
if weekday == 5:  # 토요일
    target_date = today - timedelta(days=1)
elif weekday == 6:  # 일요일
    target_date = today - timedelta(days=2)
else:
    target_date = today

default_date_str = target_date.strftime('%Y%m%d')

# 날짜 입력창 생성 (자동 계산된 날짜를 기본값으로 지정)
date_input = st.text_input('조회 날짜 (8자리)', value=default_date_str)

col1, col2 = st.columns(2)

with col1:
    st.subheader('🚨 심각한 알레르기')
    st.caption('아나필락시스 등 절대 금지')
    severe_selected = [
        k for k, v in ALLERGY_MAP.items()
        if st.checkbox(f'{v} ({k}번)', key=f'sev_{k}', value=(k == '1'))
    ]

with col2:
    st.subheader('⚠️ 경미한 알레르기')
    st.caption('가벼운 두드러기 등 주의')
    mild_selected = [
        k for k, v in ALLERGY_MAP.items()
        if st.checkbox(f'{v} ({k}번)', key=f'mild_{k}', value=(k in ['5', '6']))
    ]

if st.button('오늘의 급식 위험도 분석하기', type='primary'):
    severe_set = set(severe_selected)
    mild_set = set(mild_selected) - severe_set
    
    url = 'https://open.neis.go.kr/hub/mealServiceDietInfo'
    params = {
        'KEY': MY_NEIS_KEY.strip(),
        'Type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE,
        'SD_SCHUL_CODE': SD_SCHUL_CODE,
        'MLSV_YMD': date_input.strip(),
    }
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        if 'mealServiceDietInfo' not in data:
            st.info(
                f"🍽️ {date_input[:4]}년 {date_input[4:6]}월 {date_input[6:]}일은"
                " 학교 급식이 없는 날(주말/휴일)이거나 아직 식단표가"
                " 등록되지 않았어요!\n\n💡 내일이나 다른 평일 날짜를 선택해서"
                " 미리 확인해 보세요 😊"
            )
        else:
            row = data['mealServiceDietInfo'][1]['row'][0]
            menu_raw = row.get('DDISH_NM', '')
            
            # 메뉴 항목 분리
            menu_items = menu_raw.split('<br/>')
            
            total_risk_score = 0
            menu_cards = []
            
            for item in menu_items:
                name = re.sub(r'[0-9.\(\)]', '', item).strip()
                numbers = set(re.findall(r'\d+', item))
                
                matched_severe = numbers.intersection(severe_set)
                matched_mild = numbers.intersection(mild_set)
                
                if matched_severe:
                    total_risk_score += 35
                    severe_names = [ALLERGY_MAP.get(n, n) for n in matched_severe]
                    menu_cards.append(
                        f"🚨 **[절대 섭취 금지] {name}**\n"
                        f"- 성분: {', '.join(severe_names)}\n"
                        f"- 요령: 식판 배식 자체를 받지 마세요.\n"
                    )
                elif matched_mild:
                    total_risk_score += 15
                    mild_names = [ALLERGY_MAP.get(n, n) for n in matched_mild]
                    menu_cards.append(
                        f"⚠️ **[주의 섭취] {name}**\n"
                        f"- 성분: {', '.join(mild_names)}\n"
                        f"- 요령: 건더기 위주 소량만 섭취하세요.\n"
                    )
                else:
                    menu_cards.append(f"✅ **[안심 섭취] {name}**\n")
            
            final_score = min(total_risk_score, 100)
            
            st.divider()
            st.markdown(f"# 📊 오늘 식단 위험 점수: **{final_score}점** / 100점")
            
            if final_score == 0:
                st.success("🟢 [안심 식단] 알레르기 유발 성분이 없습니다.")
            elif final_score <= 30:
                st.warning("🟡 [주의 필요] 일부 반찬에 유발 성분이 포함되어 있습니다.")
            elif final_score <= 60:
                st.error("🟠 [경고] 심각한 유발 성분이 포함된 반찬이 있습니다.")
            else:
                st.error("🔴 [고위험 식단] 다수 메뉴 섭취 불가. 개별 안전 간식을 준비하세요.")
            
            st.subheader("📋 메뉴별 분석 결과")
            for card in menu_cards:
                st.markdown(card)
                
    except Exception as e:
        st.error(f"오류 발생: {e}")
