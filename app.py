import streamlit as st
import requests
import google.generativeai as genai
import json

# 1. 讀取 Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_KEY"]
    NEWS_API_KEY = st.secrets["NEWS_KEY"]
except:
    st.error("請檢查 Streamlit Secrets 中的 API KEY 設定。")
    st.stop()

# 2. 初始化 AI
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_model():
    # 自動偵測可用模型
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if '1.5' in m.name: return m.name
    return 'models/gemini-pro'

AVAILABLE_MODEL = get_model()
model = genai.GenerativeModel(AVAILABLE_MODEL)

st.set_page_config(page_title="Ethan's AI English", layout="wide")

# 3. 初始化歷史紀錄 (LocalStorage 模擬)
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'history' not in st.session_state: st.session_state.history = []
if 'grammar_list' not in st.session_state: st.session_state.grammar_list = []

# --- 核心功能：抓取與生成 ---
def fetch_and_generate():
    news_url = f"https://newsapi.org/v2/top-headlines?sources=bbc-news,cnn&apiKey={NEWS_API_KEY}"
    try:
        articles = requests.get(news_url).json().get('articles', [])[:3]
        context = "\n".join([f"Headline: {a['title']}\nContent: {a['description']}" for a in articles])
    except:
        return None

    prompt = f"""
    基於以下新聞內容：{context}
    請生成一個英文學習 JSON 格式，必須包含以下兩個部分：
    1. "quizzes": 5個單字測驗。包含 word(單字), kk(KK音標), options(四個繁體中文選項), answer(正確中文), 
       original_snippet(新聞原文段落), snippet_zh(段落繁中翻譯), grammar_note(文法解析與KK音標)。
    2. "daily_grammar": 5個從新聞延伸的進階文法或片語。包含 phrase(片語/文法), kk(KK音標), 
       explanation(繁體中文解釋), example(英文例句), example_zh(例句繁中翻譯)。
    
    請嚴格遵守 JSON 格式，不要輸出任何額外文字。
    """
    
    try:
        res = model.generate_content(prompt)
        raw_text = res.text.strip().lstrip('```json').rstrip('```').strip()
        return json.loads(raw_text)
    except:
        return None

# --- UI 介面 ---
st.title("🎓 Ethan 專屬新聞英文學習電台")
st.caption(f"由 AI 模型 {AVAILABLE_MODEL} 驅動 | 每日自動抓取最新新聞")

tab1, tab2, tab3, tab4 = st.tabs(["🔥 每日挑戰", "📖 錯題與歷史紀錄", "📝 每日文法片語", "⚙️ 系統設定"])

with tab1:
    if st.button("🔄 獲取今日最新教材"):
        with st.spinner('AI 正在分析新聞並標註 KK 音標...'):
            result = fetch_and_generate()
            if result:
                st.session_state.quiz_data = result['quizzes']
                st.session_state.grammar_list = result['daily_grammar']
                st.session_state.idx = 0
                st.rerun()

    if st.session_state.quiz_data:
        q = st.session_state.quiz_data[st.session_state.idx]
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### 單字：{q['word']} `[{q['kk']}]`")
            st.warning(f"**新聞原文段落：**\n{q['original_snippet']}")
            with st.expander("查看段落中文翻譯"):
                st.write(q['snippet_zh'])
            
            # 測驗選項
            st.write("---")
            for opt in q['options']:
                if st.button(opt, key=f"q_{st.session_state.idx}_{opt}"):
                    if opt == q['answer']:
                        st.success("✅ 答對了！")
                        st.balloons()
                    else:
                        st.error(f"❌ 答錯了！答案是：{q['answer']}")
                    
                    # 加入歷史紀錄
                    st.session_state.history.append({
                        "word": q['word'], "kk": q['kk'], "answer": q['answer'], "correct": (opt == q['answer'])
                    })

        with col2:
            st.info("**💡 文法解析**")
            st.write(q['grammar_note'])
            if st.button("下一題 ➡️"):
                st.session_state.idx = (st.session_state.idx + 1) % len(st.session_state.quiz_data)
                st.rerun()

with tab2:
    st.header("📚 學習歷史紀錄")
    if st.session_state.history:
        for item in reversed(st.session_state.history):
            color = "green" if item['correct'] else "red"
            st.markdown(f":{color}[**{item['word']}**] `[{item['kk']}]` - 正確答案：{item['answer']}")
    else:
        st.write("目前尚無紀錄。")

with tab3:
    st.header("📝 今日推薦文法與片語 (5組)")
    if st.session_state.grammar_list:
        for g in st.session_state.grammar_list:
            with st.container():
                st.subheader(f"{g['phrase']} `[{g['kk']}]`")
                st.write(f"**解釋：** {g['explanation']}")
                st.code(f"例句：{g['example']}\n翻譯：{g['example_zh']}")
                st.divider()
    else:
        st.write("請先回到挑戰分頁獲取內容。")

with tab4:
    if st.button("🗑️ 清除所有學習歷史"):
        st.session_state.history = []
        st.rerun()
