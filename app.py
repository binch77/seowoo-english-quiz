import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import json
import os
import random
import time
from datetime import datetime
import base64 # 이미지를 읽기 위해 필요한 도구

# 1. API 키 설정
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 로컬 테스트용 키 (배포 시 secrets가 우선됨)
    GOOGLE_API_KEY = ""

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY.strip())

# 2. 페이지 기본 설정 (브라우저 탭 아이콘은 이모티콘 유지 🦐🎓)
st.set_page_config(page_title="새우의 숙제 도우미", page_icon="🦐🎓", layout="wide")

# ==========================================
# ★ (NEW) 로컬 이미지 -> Base64 코드로 변환하는 함수 ★
# ==========================================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

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
        padding: 1rem !important; /* 모바일 여백 최소화 */
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: auto; margin-top: 10px;
    }

    /* 제목 스타일 수정 (이미지와 텍스트 정렬) */
    h1 {
        color: #FF6B6B !important; 
        text-align: center;
        font-size: 2.2rem !important;
        text-shadow: 2px 2px 0px #FFF;
        word-break: keep-all;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px; /* 이미지와 글자 사이 간격 */
    }
    
    /* 제목 옆 이미지 스타일 */
    h1 img {
        width: 50px; /* 이미지 크기 조절 */
        height: auto;
        border-radius: 10px; /* 모서리 둥글게 (선택사항) */
    }

    /* 3D 젤리 버튼 스타일 */
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
    
    /* 파일 업로더 배경 */
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

# 세션 상태 초기화
if 'quiz_data' not in st.session_state: st.session_state['quiz_data'] = []
if 'current_index' not in st.session_state: st.session_state['current_index'] = 0
if 'score' not in st.session_state: st.session_state['score'] = 0
if 'is_correct' not in st.session_state: st.session_state['is_correct'] = False
if 'retry_count' not in st.session_state: st.session_state['retry_count'] = 0
if 'wrong_answers' not in st.session_state: st.session_state['wrong_answers'] = [] 

# ==========================================
# 메인 화면 시작 (제목 부분)
# ==========================================

# ██████████████████████████████████████████████████████████████████
# ★ [중요] 여기를 수정하세요! 아빠가 준비한 진짜 파일 이름을 적어주세요 ★
# 예시: my_icon_file = "cute_shrimp.jpg"
my_icon_file = "title_icon.jpg" 
# ██████████████████████████████████████████████████████████████████

# 2. 이미지가 있으면 변환해서 넣고, 없으면 그냥 이모티콘 🦐 넣기
if os.path.exists(my_icon_file):
    # 파일을 찾았으면 코드로 변환해서 이미지 태그로 만듦
    img_b64 = get_base64_of_bin_file(my_icon_file)
    st.markdown(f"""
        <h1>
            <img src="data:image/png;base64,{img_b64}">
            서우의 영어 퀴즈
        </h1>
        """, unsafe_allow_html=True)
else:
    # 파일을 못 찾았으면 (이름이 다르거나 없으면) 그냥 기존 새우 이모티콘 사용
    st.markdown("<h1>🦐 서우의 영어 퀴즈</h1>", unsafe_allow_html=True)


# --- (아래부터는 기존과 동일합니다) ---

# 1. 지난 숙제 목록
with st.expander("📂 지난 숙제장 열기 (저장된 문제 다시 풀기)", expanded=False):
    st.caption("필요 없는 숙제는 🗑️ 버튼을 눌러서 지워요!")
    history_list = load_history()
    
    if not history_list:
        st.info("아직 저장된 숙제가 없어요! 사진을 찍어서 문제를 만들어보세요.")
    else:
        for record in history_list:
            # 모바일 보기 좋게 비율 조정 (로드 4 : 삭제 1)
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
                
                # 프롬프트: 안전장치 강화
                prompt = """
                Extract data from this English vocabulary table.
                Return ONLY a JSON array. 
                Each item must have exactly two keys: "word" and "definition".
                
                Rules:
                1. "definition" should contain the meaning. Remove any example sentences.
                2. If the definition contains the word itself, replace it with "____".
                3. Do NOT use markdown code blocks. Just raw JSON.
                
                Example: [{"word": "apple", "definition": "a round red fruit"}]
                """
                
                model = genai.GenerativeModel('gemini-flash-latest') 
                response = model.generate_content([prompt, image_parts[0]])
                
                text_response = response.text.strip()
                if text_response.startswith("```json"): text_response = text_response[7:]
                if text_response.endswith("```"): text_response = text_response[:-3]
                
                data = json.loads(text_response)
                
                # 데이터를 만들자마자 역사에 저장
                save_to_history(data)
                
                # 세션에 로드하고 퀴즈 시작
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
    
    # 상단 정보 표시 (진행바, 점수)
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
        
        # 오답 노트 출력 (틀린 게 있을 때만)
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
        
        # TTS (음성 듣기)
        try:
            tts = gTTS(text=definition_text, lang='en')
            tts.save("audio.mp3")
            st.audio("audio.mp3", format="audio/mp3")
        except: pass

        # 정답 입력창
        user_answer = st.text_input("정답을 여기에 써보세요 👇", key=f"input_{idx}")

        # 버튼 영역 (가로 배치)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            check_btn = st.button("정답 확인 ✅")
        with col_btn2:
            hint_btn = st.button("힌트 보기 🔍")
            
        if hint_btn:
             first_char = current_word[0] if len(current_word) > 0 else "?"
             st.toast(f"쉿! 첫 글자는 '{first_char}' 이야!", icon="🤫")

        # 정답 확인 로직
        if check_btn:
            if user_answer.strip().lower() == current_word.strip().lower():
                # 정답!
                st.success("제법인데 새우 👍 (+10점)")
                if not st.session_state['is_correct']:
                    st.session_state['score'] += 10
                st.session_state['is_correct'] = True # 다음 버튼 활성화
                st.session_state['retry_count'] = 0 
                st.balloons()
                
                good_img = find_image_file("good")
                if good_img: st.image(good_img, caption="정답이야 새우 대단해!")
            else:
                # 오답!
                if st.session_state['retry_count'] == 0:
                    # 첫 번째 틀림 (기회 부여)
                    st.warning("아까비! 한 번만 더 생각해볼까? 🤔 (기회 1번 남음!)")
                    st.session_state['retry_count'] += 1
                else:
                    # 두 번째 틀림 (정답 공개 및 넘어가기)
                    st.error(f"땡! 정답은 '{current_word}' 였어.")
                    # 오답 노트에 추가
                    if question not in st.session_state['wrong_answers']:
                        st.session_state['wrong_answers'].append(question)
                    
                    bad_img = find_image_file("bad")
                    if bad_img: st.image(bad_img, caption="틀렸어 새우 ㅠㅠ")
                    
                    st.session_state['is_correct'] = True # 틀렸지만 다음으로 넘어가게 해줌
                    st.session_state['retry_count'] = 0 

        # 다음 문제로 넘어가는 버튼
        if st.session_state['is_correct']:
            st.write("")
            if st.button("다음 문제로 고고! ➡️", type="primary"):
                st.session_state['current_index'] += 1
                st.session_state['is_correct'] = False
                st.session_state['retry_count'] = 0

                st.rerun()
