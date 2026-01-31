import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import json
import os
import random
import time
from datetime import datetime
import base64 
import streamlit.components.v1 as components
import io  # ★ 메모리 기반 오디오 처리를 위해 추가
import difflib  # ★ 너그러운 채점(오타 허용)을 위해 추가

# 1. API 키 설정
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 로컬 테스트용 키
    GOOGLE_API_KEY = ""

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY.strip())

# 2. 페이지 기본 설정
st.set_page_config(page_title="새우의 숙제 도우미", page_icon="🦐🎓", layout="wide")

# ==========================================
# ★ (NEW) 로컬 이미지 -> Base64 코드로 변환하는 함수 ★
# ==========================================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ==========================================
# ★ (NEW) 자동완성 끄기 함수 ★
# ==========================================
def disable_autocomplete():
    components.html(
        """
        <script>
            const inputs = window.parent.document.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                input.setAttribute('autocomplete', 'off');
            });
        </script>
        """,
        height=0
    )

# ==========================================
# ★ 저장/불러오기/삭제 관련 함수 ★
# ==========================================
HISTORY_FILE = 'quiz_history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_to_history(new_data):
    history = load_history()
    
    days = ['월', '화', '수', '목', '금', '토', '일']
    now = datetime.now()
    weekday = days[now.weekday()]
    title = now.strftime(f"%Y년 %m월 %d일 ({weekday})의 숙제")
    
    new_record = {
        "id": str(now.timestamp()),
        "title": title,
        "data": new_data,
        "date": now.strftime("%Y-%m-%d")
    }
    history.insert(0, new_record)
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def delete_history_item(record_id):
    history = load_history()
    new_history = [item for item in history if item['id'] != record_id]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=4)

# ==========================================
# ★ 디자인 (CSS) ★
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
        border-radius: 20px;
        padding: 1rem !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: auto; margin-top: 10px;
    }

    h1 {
        color: #FF6B6B !important; 
        text-align: center;
        font-size: 2.2rem !important;
        text-shadow: 2px 2px 0px #FFF;
        word-break: keep-all;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }
    
    h1 img {
        width: 50px;
        height: auto;
        border-radius: 10px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 15px !important;
        background: linear-gradient(to bottom, #FF9A9E 0%, #FECFEF 100%) !important;
        color: white !important;
        border: none !important;
        border-bottom: 5px solid #FF6B6B !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        padding: 10px 0 !important;
        transition: all 0.1s;
        margin-top: 5px;
    }
    .stButton > button:active {
        transform: translateY(4px);
        border-bottom: 2px solid #FF6B6B !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] {
        border-radius: 15px !important;
        border: 3px solid #FFD1FF !important;
        background-color: #FFFAF0 !important;
        padding: 5px; font-size: 1.2rem; text-align: center !important;
    }
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 15px !important; border: none !important;
        padding: 10px !important; font-size: 1rem !important;
        text-align: center !important;
    }
    .stSuccess { background-color: #E8F5E9 !important; color: #2E7D32 !important; }
    .stError { background-color: #FFEBEE !important; color: #C62828 !important; }
    .stWarning { background-color: #FFF3E0 !important; color: #E65100 !important; }
    .stProgress > div > div > div > div { background-color: #FF9A9E !important; }
    
    [data-testid='stFileUploader'] section {
        background-color: #FFF0F5; border: 2px dashed #FFB6C1; border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 메인 로직 ---

def find_image_file(base_name):
    for ext in [".png", ".jpg", ".jpeg"]:
        file_path = base_name + ext
        if os.path.exists(file_path): return file_path
    return None

def calculate_similarity(a, b):
    # 두 문자열의 유사도를 0~1 사이로 반환 (difflib 활용)
    return difflib.SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()

# 세션 상태 초기화
if 'quiz_data' not in st.session_state: st.session_state['quiz_data'] = []
if 'current_index' not in st.session_state: st.session_state['current_index'] = 0
if 'score' not in st.session_state: st.session_state['score'] = 0
if 'is_correct' not in st.session_state: st.session_state['is_correct'] = False
if 'retry_count' not in st.session_state: st.session_state['retry_count'] = 0
if 'wrong_answers' not in st.session_state: st.session_state['wrong_answers'] = [] 

# ==========================================
# 메인 화면 시작
# ==========================================

my_icon_file = "title_icon.jpg" 

if os.path.exists(my_icon_file):
    try:
        img_b64 = get_base64_of_bin_file(my_icon_file)
        st.markdown(f"""
            <h1>
                <img src="data:image/png;base64,{img_b64}">
                서우의 영어 퀴즈
            </h1>
            """, unsafe_allow_html=True)
    except:
        st.markdown("<h1>🦐 서우의 영어 퀴즈</h1>", unsafe_allow_html=True)
else:
    st.markdown("<h1>🦐 서우의 영어 퀴즈</h1>", unsafe_allow_html=True)

# 1. 지난 숙제 목록
with st.expander("📂 지난 숙제장 열기 (저장된 문제 다시 풀기)", expanded=False):
    st.caption("필요 없는 숙제는 🗑️ 버튼을 눌러서 지워요!")
    history_list = load_history()
    
    if not history_list:
        st.info("아직 저장된 숙제가 없어요! 사진을 찍어서 문제를 만들어보세요.")
    else:
        for record in history_list:
            col_load, col_del = st.columns([4, 1])
            with col_load:
                if st.button(f"{record['title']}", key=f"load_{record['id']}"):
                    st.session_state['quiz_data'] = record['data']
                    st.session_state['current_index'] = 0
                    st.session_state['score'] = 0
                    st.session_state['is_correct'] = False
                    st.session_state['retry_count'] = 0
                    st.session_state['wrong_answers'] = []
                    random.shuffle(st.session_state['quiz_data']) 
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{record['id']}"):
                    delete_history_item(record['id'])
                    st.rerun()

# 2. 사진 업로드
with st.expander("📸 새로운 문제지 사진 찍기 (클릭!)", expanded=not st.session_state['quiz_data']):
    img_file = st.file_uploader("단어장 사진을 올려주세요", type=['png', 'jpg', 'jpeg'])

# 3. AI 분석 및 저장 실행
if img_file is not None:
    if st.button("이 사진으로 문제 만들기 🚀"):
        with st.spinner('💖 새우가 열심히 단어를 읽고 있어요...'):
            try:
                bytes_data = img_file.getvalue()
                image_parts = [{"mime_type": img_file.type, "data": bytes_data}]
                
                # ★★★ [수정됨] 프롬프트를 다시 '영어 정의' 추출로 변경했습니다! ★★★
                prompt = """
                Extract data from this English vocabulary table.
                Return ONLY a valid JSON array of objects. 
                Each object must have exactly: "word" and "definition".
                
                Rules:
                1. "definition" should be the English definition found in the image. 
                2. If the definition contains the word itself, replace it with "____".
                3. Remove any example sentences, keep only the definition.
                4. NO markdown blocks. Just the raw JSON array.
                
                Example: [{"word": "apple", "definition": "a round red fruit"}]
                """
                
                model = genai.GenerativeModel('gemini-flash-latest') 
                response = model.generate_content([prompt, image_parts[0]])
                
                text_response = response.text.strip()
                # 마크다운 태그 제거용 안전장치
                if "```" in text_response:
                    text_response = text_response.split("```")[1]
                    if text_response.startswith("json"):
                        text_response = text_response[4:]
                
                data = json.loads(text_response)
                save_to_history(data)
                
                random.shuffle(data)
                st.session_state['quiz_data'] = data
                st.session_state['current_index'] = 0
                st.session_state['score'] = 0
                st.session_state['is_correct'] = False
                st.session_state['retry_count'] = 0
                st.session_state['wrong_answers'] = []
                st.rerun()
                
            except Exception as e:
                st.error(f"오류가 났어요: {e}")

# 4. 퀴즈 진행 로직
if st.session_state['quiz_data']:
    total_q = len(st.session_state['quiz_data'])
    idx = st.session_state['current_index']
    
    col1, col2 = st.columns([7, 3])
    with col1:
        st.caption(f"문제 푸는 중 ({idx}/{total_q})")
        progress_val = min((idx) / total_q, 1.0)
        st.progress(progress_val)
    with col2:
        st.markdown(f"<div style='background:#FFF0F5; padding:5px; border-radius:10px; text-align:center; color:#FF69B4; font-weight:bold; font-size:1.1rem; box-shadow:0 2px 5px rgba(0,0,0,0.05);'>🏆 {st.session_state['score']}</div>", unsafe_allow_html=True)

    st.divider()

    # --- 퀴즈 종료 화면 ---
    if idx >= total_q:
        st.balloons()
        st.markdown(f"<h2 style='text-align:center; color:#FF6B6B;'>🎉 숙제 끝! 🎉</h2>", unsafe_allow_html=True)
        st.info(f"최종 점수: {st.session_state['score']}점 / {total_q * 10}점")
        
        good_img = find_image_file("good")
        if good_img: st.image(good_img, use_container_width=True)
        
        if st.session_state['wrong_answers']:
            st.markdown("---")
            st.markdown("<h3 style='color:#C62828; text-align:center;'>📝 오답 노트</h3>", unsafe_allow_html=True)
            for item in st.session_state['wrong_answers']:
                w = item.get('word', '단어 없음')
                d = item.get('definition', '뜻 없음')
                st.error(f"**{w}** : {d}")
            st.markdown("---")
            
        if st.button("처음부터 다시 하기"):
            st.session_state['quiz_data'] = []
            st.session_state['current_index'] = 0
            st.session_state['score'] = 0
            st.session_state['is_correct'] = False
            st.session_state['retry_count'] = 0
            st.session_state['wrong_answers'] = [] 
            st.rerun()
            
    # --- 문제 풀이 화면 ---
    else:
        question = st.session_state['quiz_data'][idx]
        definition_text = question.get('definition', "⚠️ 뜻을 불러올 수 없어요.")
        current_word = question.get('word', "Unknown")

        st.markdown(f"<h3 style='text-align:center; margin-bottom:0;'>🎈 문제 {idx + 1}</h3>", unsafe_allow_html=True)
        st.info(f"{definition_text}")
        
        # ★ 메모리 기반 오디오 생성 (BytesIO) ★
        try:
            tts = gTTS(text=definition_text, lang='en')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            st.audio(audio_fp, format="audio/mp3")
        except: pass

        # 정답 입력창
        user_answer = st.text_input("정답을 여기에 써보세요 👇", key=f"input_{idx}")
        disable_autocomplete()

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            check_btn = st.button("정답 확인 ✅")
        with col_btn2:
            hint_btn = st.button("힌트 보기 🔍")
            
        if hint_btn:
             first_char = current_word[0] if len(current_word) > 0 else "?"
             st.toast(f"쉿! 첫 글자는 '{first_char}' 이야!", icon="🤫")

        if check_btn:
            similarity = calculate_similarity(user_answer, current_word)
            
            # 1. 완벽한 정답
            if similarity == 1.0:
                st.success("대박! 완벽한 정답이야 👍 (+10점)")
                if not st.session_state['is_correct']:
                    st.session_state['score'] += 10
                st.session_state['is_correct'] = True
                st.session_state['retry_count'] = 0 
                st.balloons()
                good_img = find_image_file("good")
                if good_img: st.image(good_img, caption="정답이야 새우 대단해!")
            
            # 2. 아주 아까운 오타 (유사도 80% 이상)
            elif similarity >= 0.8:
                st.warning("오... 거의 다 맞았어! 스펠링을 한 번만 더 확인해볼까? 🤔")
                # 기회를 한 번 더 줌 (카운트 증가 X)
            
            # 3. 틀림
            else:
                if st.session_state['retry_count'] == 0:
                    st.warning("아까비! 한 번만 더 생각해볼까? (기회 1번 남음!)")
                    st.session_state['retry_count'] += 1
                else:
                    st.error(f"땡! 정답은 '{current_word}' 였어.")
                    if question not in st.session_state['wrong_answers']:
                        st.session_state['wrong_answers'].append(question)
                    bad_img = find_image_file("bad")
                    if bad_img: st.image(bad_img, caption="틀렸어 새우 ㅠㅠ")
                    st.session_state['is_correct'] = True 
                    st.session_state['retry_count'] = 0 

        if st.session_state['is_correct']:
            st.write("")
            if st.button("다음 문제로 고고! ➡️", type="primary"):
                st.session_state['current_index'] += 1
                st.session_state['is_correct'] = False
                st.session_state['retry_count'] = 0
                st.rerun()
