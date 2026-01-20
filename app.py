import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import json
import os
import random
import time

# 1. API 키 설정 (★중요: 본인의 키를 다시 넣어주세요!)
GOOGLE_API_KEY = "AIzaSyBUp9YNp86b7JV2p3HZluI9DgtosG3J-T0"

# 공백 제거 안전장치
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY.strip())

# 2. 페이지 기본 설정
st.set_page_config(page_title="새우의 숙제 도우미", page_icon="🍤")

# ==========================================
# ★ 디자인 마법 코드 (CSS) - 모바일 최적화 & 3D 버튼 ★
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
    html, body, [class*="css"]  { font-family: 'Jua', sans-serif !important; }

    /* 전체 배경 */
    .stApp {
        background-image: linear-gradient(to top, #fad0c4 0%, #ffd1ff 100%);
        background-attachment: fixed;
    }

    /* 하얀색 카드 (모바일 여백 조정) */
    .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 1.5rem 1rem !important; /* 모바일에서 여백 줄임 */
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: auto; margin-top: 10px;
    }

    /* 제목 스타일 (모바일 줄바꿈 방지) */
    h1 {
        color: #FF6B6B !important; 
        text-align: center;
        font-size: 2.5rem !important; /* 글자 크기 약간 줄임 */
        padding-bottom: 10px;
        text-shadow: 2px 2px 0px #FFF, 3px 3px 0px rgba(0,0,0,0.1);
        word-break: keep-all; /* 단어 중간에 줄바꿈 금지 */
        line-height: 1.2;
    }

    /* ★ 3D 입체 젤리 버튼 스타일 ★ */
    .stButton > button {
        width: 100%;
        border-radius: 15px !important;
        background: linear-gradient(to bottom, #FF9A9E 0%, #FECFEF 100%) !important;
        color: white !important;
        border: none !important;
        border-bottom: 6px solid #FF6B6B !important; /* 입체감을 위한 바닥 두께 */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        padding: 10px 0 !important;
        transition: all 0.1s;
        margin-top: 5px;
        height: auto !important;
    }
    
    /* 버튼 눌렀을 때 (쏙 들어가는 효과) */
    .stButton > button:active {
        transform: translateY(4px); /* 아래로 이동 */
        border-bottom: 2px solid #FF6B6B !important; /* 두께 얇아짐 */
        box-shadow: none !important;
    }
    
    /* 힌트 버튼 색상 변경 (파란색 계열) */
    div[data-testid="column"]:nth-of-type(2) .stButton > button {
        background: linear-gradient(to bottom, #89f7fe 0%, #66a6ff 100%) !important;
        border-bottom: 6px solid #005bea !important;
    }
    div[data-testid="column"]:nth-of-type(2) .stButton > button:active {
        border-bottom: 2px solid #005bea !important;
    }

    /* 입력창 스타일 */
    div[data-baseweb="input"] {
        border-radius: 15px !important;
        border: 3px solid #FFD1FF !important;
        background-color: #FFFAF0 !important;
        padding: 5px; font-size: 1.2rem; text-align: center !important;
    }
    
    /* 모바일에서 버튼 강제로 가로 정렬하기 */
    div[data-testid="column"] {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 50% !important;
    }
    
    /* 알림박스 */
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 15px !important; border: none !important;
        padding: 10px !important; font-size: 1rem !important;
        text-align: center !important;
    }
    .stSuccess { background-color: #E8F5E9 !important; color: #2E7D32 !important; }
    .stError { background-color: #FFEBEE !important; color: #C62828 !important; }
    .stWarning { background-color: #FFF3E0 !important; color: #E65100 !important; }

    /* 기타 */
    .stProgress > div > div > div > div { background-color: #FF9A9E !important; }
    [data-testid='stFileUploader'] section {
        background-color: #FFF0F5; border: 2px dashed #FFB6C1; border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 메인 로직 시작 ---

st.markdown("<h1>🍤 서우의 영어 퀴즈</h1>", unsafe_allow_html=True)

# 이미지 찾기 함수
def find_image_file(base_name):
    for ext in [".png", ".jpg", ".jpeg"]:
        file_path = base_name + ext
        if os.path.exists(file_path): return file_path
    return None

# 3. 사진 업로드
with st.expander("📸 여기가 문제지 넣는 곳이야 (클릭!)", expanded=True):
    img_file = st.file_uploader("단어장 사진을 찰칵!", type=['png', 'jpg', 'jpeg'])

# 세션 초기화
if 'quiz_data' not in st.session_state: st.session_state['quiz_data'] = []
if 'current_index' not in st.session_state: st.session_state['current_index'] = 0
if 'score' not in st.session_state: st.session_state['score'] = 0
if 'is_correct' not in st.session_state: st.session_state['is_correct'] = False # '다음 문제로 넘어갈 수 있는 상태'를 의미
if 'retry_count' not in st.session_state: st.session_state['retry_count'] = 0
if 'wrong_answers' not in st.session_state: st.session_state['wrong_answers'] = [] 

# 4. AI 분석
if img_file is not None and not st.session_state['quiz_data']:
    with st.spinner('🍤 새우가 열심히 단어를 읽고 있어요...'):
        try:
            bytes_data = img_file.getvalue()
            image_parts = [{"mime_type": img_file.type, "data": bytes_data}]
            
            prompt = """
            이 이미지는 영어 단어장이야. 표에서 'English Word'(단어)와 'Definition / Example'(정의 및 예문)을 읽어줘.
            중요한 규칙:
            1. 'Definition / Example' 칸에는 정의(Definition)와 예문(Example)이 같이 들어있다.
            2. 예문(Example)은 보통 두 번째 문장이거나 정답 단어가 포함된 문장이다.
            3. 결과에는 예문을 과감히 삭제하고, 오직 '정의(Definition)' 문장만 남겨서 추출해라.
            4. 만약 정의 문장 안에도 정답 단어가 있다면, 그 단어를 '____' (빈칸)으로 바꿔라.
            결과는 반드시 순수한 JSON 형식으로만 줘. 마크다운 없이 텍스트만 줘.
            형식: [{"word": "cartwheel", "definition": "to turn sideways on your hands and land on your feet."}]
            """
            
            model = genai.GenerativeModel('gemini-flash-latest') 
            response = model.generate_content([prompt, image_parts[0]])
            
            text_response = response.text.strip()
            if text_response.startswith("```json"): text_response = text_response[7:]
            if text_response.endswith("```"): text_response = text_response[:-3]
            
            data = json.loads(text_response)
            random.shuffle(data)
            
            st.session_state['quiz_data'] = data
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"오류가 났어요: {e}")

# 5. 퀴즈 진행
if st.session_state['quiz_data']:
    total_q = len(st.session_state['quiz_data'])
    idx = st.session_state['current_index']
    
    # 상단 정보 (모바일 가독성 개선)
    col1, col2 = st.columns([7, 3])
    with col1:
        st.caption(f"문제 푸는 중 ({idx}/{total_q})")
        progress_val = min((idx) / total_q, 1.0)
        st.progress(progress_val)
    with col2:
        st.markdown(f"<div style='background:#FFF0F5; padding:5px; border-radius:10px; text-align:center; color:#FF69B4; font-weight:bold; font-size:1.1rem; box-shadow:0 2px 5px rgba(0,0,0,0.05);'>🏆 {st.session_state['score']}</div>", unsafe_allow_html=True)

    st.divider()

    if idx >= total_q:
        # 종료 화면
        st.balloons()
        st.markdown(f"<h2 style='text-align:center; color:#FF6B6B;'>🎉 숙제 끝! 🎉</h2>", unsafe_allow_html=True)
        st.info(f"최종 점수: {st.session_state['score']}점 / {total_q * 10}점")
        
        good_img = find_image_file("good")
        if good_img: st.image(good_img, use_container_width=True)
        
        if st.session_state['wrong_answers']:
            st.markdown("---")
            st.markdown("<h3 style='color:#C62828; text-align:center;'>📝 오답 노트</h3>", unsafe_allow_html=True)
            for item in st.session_state['wrong_answers']:
                st.error(f"**{item['word']}** : {item['definition']}")
            st.markdown("---")
            
        if st.button("처음부터 다시 하기"):
            st.session_state['quiz_data'] = []
            st.session_state['current_index'] = 0
            st.session_state['score'] = 0
            st.session_state['is_correct'] = False
            st.session_state['retry_count'] = 0
            st.session_state['wrong_answers'] = [] 
            st.rerun()
    else:
        question = st.session_state['quiz_data'][idx]
        
        # 문제 표시
        st.markdown(f"<h3 style='text-align:center; margin-bottom:0;'>🎈 문제 {idx + 1}</h3>", unsafe_allow_html=True)
        st.info(f"{question['definition']}")
        
        try:
            tts_text = question['definition']
            tts = gTTS(text=tts_text, lang='en')
            tts.save("audio.mp3")
            st.audio("audio.mp3", format="audio/mp3")
        except: pass

        # 정답 입력
        user_answer = st.text_input("정답을 여기에 써보세요 👇", key=f"input_{idx}")

        # ★ 모바일 버튼 가로 정렬 수정 ★
        # 복잡한 컬럼 중첩을 없애고 단순하게 갑니다.
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            check_btn = st.button("정답 확인 ✅")
        with col_btn2:
            hint_btn = st.button("힌트 보기 🔍")
            
        if hint_btn:
             st.toast(f"쉿! 첫 글자는 '{question['word'][0]}' 이야!", icon="🤫")

        # ★핵심 로직 수정: 2번 틀리면 다음으로 넘어가게 하기★
        if check_btn:
            if user_answer.strip().lower() == question['word'].strip().lower():
                # 정답!
                st.success("제법인데 새우 👍 (+10점)")
                if not st.session_state['is_correct']:
                    st.session_state['score'] += 10
                st.session_state['is_correct'] = True # 다음 버튼 나옴
                st.session_state['retry_count'] = 0 
                st.balloons()
                
                good_img = find_image_file("good")
                if good_img: st.image(good_img, caption="정답이야 새우 대단해!")
            else:
                # 오답!
                if st.session_state['retry_count'] == 0:
                    # 기회 1번 남음
                    st.warning("아까비! 한 번만 더 생각해볼까? 🤔 (기회 1번 남음!)")
                    st.session_state['retry_count'] += 1
                else:
                    # 2번 틀림 -> 정답 공개하고 다음으로 넘어가게 해줌
                    st.error(f"땡! 정답은 '{question['word']}' 였어.")
                    
                    if question not in st.session_state['wrong_answers']:
                        st.session_state['wrong_answers'].append(question)
                        
                    bad_img = find_image_file("bad")
                    if bad_img: st.image(bad_img, caption="틀렸어 새우 ㅠㅠ")
                    
                    # ★여기가 중요★: 틀렸지만, 다음 문제로 넘어갈 수 있게 버튼을 활성화합니다.
                    st.session_state['is_correct'] = True 
                    st.session_state['retry_count'] = 0 

        # 다음 문제 버튼 (정답을 맞췄거나, 2번 틀려서 정답을 확인한 경우)
        if st.session_state['is_correct']:
            st.write("")
            if st.button("다음 문제로 고고! ➡️", type="primary"):
                st.session_state['current_index'] += 1
                st.session_state['is_correct'] = False
                st.session_state['retry_count'] = 0
                st.rerun()