import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import json
import os
import random
import time

# 클라우드 금고에서 키를 가져오는 방식입니다
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 내 컴퓨터에서 테스트할 때는 여기에 키를 넣으세요 (업로드할 땐 지우는 게 좋아요)
    GOOGLE_API_KEY = ""

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY.strip())

# 2. 페이지 기본 설정
st.set_page_config(page_title="새우의 숙제 도우미", page_icon="🍤")

# ==========================================
# ★ 디자인 마법 코드 (CSS) ★
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
    html, body, [class*="css"]  { font-family: 'Jua', sans-serif !important; }

    .stApp {
        background-image: linear-gradient(to top, #fad0c4 0%, #ffd1ff 100%);
        background-attachment: fixed;
    }

    .block-container {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 30px;
        padding: 2rem !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: auto; margin-top: 20px;
    }

    h1 {
        color: #FF6B6B !important; text-align: center;
        font-size: 3rem !important; padding-bottom: 10px;
        text-shadow: 2px 2px 0px #FFF, 4px 4px 0px rgba(0,0,0,0.1);
    }

    .stButton > button {
        width: 100%;
        border-radius: 50px !important;
        background: linear-gradient(to bottom, #FF9A9E 0%, #FECFEF 100%) !important;
        color: white !important;
        border: 3px solid white !important;
        box-shadow: 0 4px 10px rgba(255, 105, 135, 0.3) !important;
        font-size: 1.2rem !important; font-weight: bold !important;
        padding: 12px 0 !important; transition: all 0.2s;
        display: flex; justify-content: center; align-items: center;
    }
    .stButton > button:hover { transform: scale(1.03) translateY(-2px); }
    .stButton > button:active { transform: scale(0.98); }

    div[data-baseweb="input"] {
        border-radius: 30px !important;
        border: 3px solid #FFD1FF !important;
        background-color: #FFFAF0 !important;
        padding: 8px 15px; font-size: 1.1rem; text-align: center !important;
    }
    
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 20px !important; border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        padding: 15px !important; font-size: 1.1rem !important;
        text-align: center !important;
    }
    .stSuccess { background-color: #E8F5E9 !important; color: #2E7D32 !important; }
    .stError { background-color: #FFEBEE !important; color: #C62828 !important; }
    .stWarning { background-color: #FFF3E0 !important; color: #E65100 !important; }

    .stProgress > div > div > div > div { background-color: #FF9A9E !important; }
    [data-testid='stFileUploader'] section {
        background-color: #FFF0F5; border: 2px dashed #FFB6C1; border-radius: 20px;
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
if 'is_correct' not in st.session_state: st.session_state['is_correct'] = False
if 'retry_count' not in st.session_state: st.session_state['retry_count'] = 0
if 'wrong_answers' not in st.session_state: st.session_state['wrong_answers'] = [] # ★오답노트 저장소★

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
    
    # 상단 정보
    col1, col2 = st.columns([7, 3])
    with col1:
        st.caption(f"문제 푸는 중 ({idx}/{total_q})")
        progress_val = min((idx) / total_q, 1.0)
        st.progress(progress_val)
    with col2:
        st.markdown(f"<div style='background:#FFF0F5; padding:8px; border-radius:15px; text-align:center; color:#FF69B4; font-weight:bold; font-size:1.2rem; box-shadow:0 2px 5px rgba(0,0,0,0.05);'>🏆 {st.session_state['score']}점</div>", unsafe_allow_html=True)

    st.divider()

    if idx >= total_q:
        # 종료 화면
        st.balloons()
        st.markdown(f"<h2 style='text-align:center; color:#FF6B6B;'>🎉 숙제 끝! 🎉</h2>", unsafe_allow_html=True)
        st.info(f"최종 점수: {st.session_state['score']}점 / {total_q * 10}점")
        
        good_img = find_image_file("good")
        if good_img: st.image(good_img, use_container_width=True)
        
        # ★ 오답 노트 보여주기 (틀린 문제가 있을 때만) ★
        if st.session_state['wrong_answers']:
            st.markdown("---")
            st.markdown("<h3 style='color:#C62828;'>📝 오늘 서우가 헷갈려한 단어들</h3>", unsafe_allow_html=True)
            for item in st.session_state['wrong_answers']:
                st.error(f"**{item['word']}** : {item['definition']}")
            st.markdown("---")
            
        if st.button("처음부터 다시 하기"):
            st.session_state['quiz_data'] = []
            st.session_state['current_index'] = 0
            st.session_state['score'] = 0
            st.session_state['is_correct'] = False
            st.session_state['retry_count'] = 0
            st.session_state['wrong_answers'] = [] # 오답노트 초기화
            st.rerun()
    else:
        question = st.session_state['quiz_data'][idx]
        
        # 문제 표시
        st.markdown(f"<h3 style='text-align:center;'>🎈 문제 {idx + 1}</h3>", unsafe_allow_html=True)
        st.info(f"{question['definition']}")
        
        # 오디오
        try:
            tts_text = question['definition']
            tts = gTTS(text=tts_text, lang='en')
            tts.save("audio.mp3")
            st.audio("audio.mp3", format="audio/mp3")
        except: pass

        # 정답 입력
        user_answer = st.text_input("정답을 여기에 써보세요 👇", key=f"input_{idx}")

        # 버튼 영역
        col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
        with col_b2:
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1: check_btn = st.button("정답 확인 ✅")
            with sub_c2: hint_btn = st.button("힌트 보기 🔍")
            
        if hint_btn:
             st.toast(f"쉿! 첫 글자는 '{question['word'][0]}' 이야!", icon="🤫")

        # 정답 확인 로직
        if check_btn:
            if user_answer.strip().lower() == question['word'].strip().lower():
                st.success("제법인데 새우 👍 (+10점)")
                if not st.session_state['is_correct']:
                    st.session_state['score'] += 10
                st.session_state['is_correct'] = True
                st.session_state['retry_count'] = 0
                st.balloons()
                
                good_img = find_image_file("good")
                if good_img: st.image(good_img, caption="정답이야 새우 대단해!")
            else:
                if st.session_state['retry_count'] == 0:
                    st.warning("오~이런 새우야! 한 번만 더 생각해볼까? 🤔 (기회 1번 남음!)")
                    st.session_state['retry_count'] += 1
                else:
                    st.error(f"땡! 정답은 '{question['word']}' 였어.")
                    
                    # ★ 오답 노트에 추가 (중복 방지) ★
                    if question not in st.session_state['wrong_answers']:
                        st.session_state['wrong_answers'].append(question)
                        
                    bad_img = find_image_file("bad")
                    if bad_img: st.image(bad_img, caption="틀렸어 새우 ㅠㅠ")
                    st.session_state['is_correct'] = False 
                    st.session_state['retry_count'] = 0

        # 다음 문제 버튼
        if st.session_state['is_correct']:
            st.write("")
            col_n1, col_n2, col_n3 = st.columns([1, 2, 1])
            with col_n2:
                if st.button("다음 문제로 고고! ➡️"):
                    st.session_state['current_index'] += 1
                    st.session_state['is_correct'] = False
                    st.session_state['retry_count'] = 0

                    st.rerun()
