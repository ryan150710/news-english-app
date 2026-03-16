import streamlit as st
import requests
import google.generativeai as genai
import json

# 1. 讀取 Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_KEY"]
    NEWS_API_KEY = st.secrets["NEWS_KEY"]
except Exception as e:
    st.error("Secrets 設定錯誤，請確認 GEMINI_KEY 與 NEWS_KEY 是否已填寫。")
    st.stop()

# 2. 初始化 AI 並找出可用模型
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def find_available_model():
    try:
        # 列出所有可用的模型
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 優先選擇 flash 或 pro 1.5 版本
                if '1.5' in m.name:
                    return m.name
        # 如果找不到 1.5，隨便回傳第一個支援生成內容的模型
        return 'models/gemini-pro' 
    except Exception as e:
        st.error(f"無法列出模型清單: {e}")
        return 'models/gemini-pro'

AVAILABLE_MODEL = find_available_model()

st.set_page_config(page_title="NewsVocab AI", layout="centered")

def get_daily_quiz():
    news_url = f"https://newsapi.org/v2/top-headlines?sources=bbc-news,cnn,reuters&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(news_url).json()
        articles = response.get('articles', [])[:5]
        context_text = "\n".join([f"News: {a['title']}" for a in articles])
    except:
        st.error("新聞抓取失敗")
        return []

    prompt = f"""
    Based on these news: {context_text}
    Generate 5 English vocabulary quiz items in JSON format.
    Output ONLY a raw JSON list.
    Structure: [{{"word": "..", "options": ["..", "..", "..", ".."], "answer": "..", "sentence": "..", "link": "..", "grammar": ".."}}]
    """

    try:
        # 使用偵測到的可用模型
        model = genai.GenerativeModel(AVAILABLE_MODEL)
        res = model.generate_content(prompt)
        raw_text = res.text.strip()
        
        # 清理 JSON 標籤
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        return json.loads(raw_text)
    except Exception as e:
        st.error(f"目前使用的模型 {AVAILABLE_MODEL} 生成出錯: {e}")
        return []

# --- UI 介面 ---
st.title("🗞️ NewsVocab AI 學習電台")
st.caption(f"系統偵測到可用模型: {AVAILABLE_MODEL}")

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = []
    st.session_state.idx = 0
    st.session_state.mistakes = []

tab1, tab2, tab3 = st.tabs(["🔥 每日測驗", "📚 錯題複習", "📖 文法解析"])

with tab1:
    if st.button("🔄 獲取今日 AI 題目"):
        with st.spinner('AI 正在讀報紙...'):
            data = get_daily_quiz()
            if data:
                st.session_state.quiz_data = data
                st.session_state.idx = 0
                st.rerun()

    if st.session_state.quiz_data:
        curr = st.session_state.quiz_data[st.session_state.idx]
        st.subheader(f"單字：{curr['word']}")
        st.info(f"Context: {curr['sentence']}")
        
        for opt in curr['options']:
            if st.button(opt, key=f"btn_{opt}"):
                if opt == curr['answer']:
                    st.success("✅ 答對了！")
                    st.balloons()
                else:
                    st.error(f"❌ 答錯！答案是：{curr['answer']}")
                    if curr not in st.session_state.mistakes:
                        st.session_state.mistakes.append(curr)
        
        if st.button("下一題 ➡️"):
            st.session_state.idx = (st.session_state.idx + 1) % len(st.session_state.quiz_data)
            st.rerun()

with tab2:
    if st.session_state.mistakes:
        for m in st.session_state.mistakes:
            st.write(f"**{m['word']}** : {m['answer']}")
    else:
        st.write("目前沒有錯題。")

with tab3:
    if st.session_state.quiz_data:
        q = st.session_state.quiz_data[st.session_state.idx]
        st.write(q['grammar'])
        st.caption(f"[查看新聞原文]({q['link']})")
