import streamlit as st
import requests
import google.generativeai as genai
import json

# 從 Streamlit 安全設定中讀取金鑰
GEMINI_API_KEY = st.secrets["GEMINI_KEY"]
NEWS_API_KEY = st.secrets["NEWS_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="NewsVocab AI", layout="centered")

# 將 models/gemini-1.5-flash 改為 gemini-1.5-flash-latest 或 gemini-pro
model = genai.GenerativeModel('gemini-1.5-flash-latest')
def get_daily_quiz():
    news_url = f"https://newsapi.org/v2/top-headlines?sources=bbc-news,cnn,reuters&apiKey={NEWS_API_KEY}"
    response = requests.get(news_url).json()
    articles = response.get('articles', [])[:5]
    
    if not articles:
        return []

    context_text = "\n".join([f"Title: {a['title']}" for a in articles])

    # 1. 嘗試使用 -latest 結尾的名稱
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"""
        Based on these news articles: {context_text}
        Generate 5 English vocabulary quiz items in JSON format.
        Return ONLY a raw JSON list.
        Structure: [{{"word": "...", "options": ["...", "..."], "answer": "...", "sentence": "...", "link": "...", "grammar": "..."}}]
        """
        
        res = model.generate_content(prompt)
        # 2. 增加更安全的解析邏輯
        text_content = res.text.strip()
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0].strip()
        elif "```" in text_content:
            text_content = text_content.split("```")[1].split("```")[0].strip()
            
        return json.loads(text_content)
    except Exception as e:
        st.error(f"AI 生成出錯: {e}")
        return []
        
# 狀態初始化
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = []
    st.session_state.idx = 0
    st.session_state.mistakes = []

st.title("🗞️ NewsVocab AI 學習電台")

tab1, tab2, tab3 = st.tabs(["🔥 每日測驗", "📚 錯題複習", "📖 文法解析"])

with tab1:
    if st.button("🔄 獲取今日 AI 題目"):
        with st.spinner('正在分析 BBC/CNN...'):
            st.session_state.quiz_data = get_daily_quiz()
            st.session_state.idx = 0
    
    if st.session_state.quiz_data:
        q = st.session_state.quiz_data[st.session_state.idx]
        st.subheader(f"單字：{q['word']}")
        st.info(f"Context: {q['sentence']}")
        
        for opt in q['options']:
            if st.button(opt, key=opt):
                if opt == q['answer']:
                    st.success("✅ 正確！")
                    st.balloons()
                else:
                    st.error(f"❌ 錯誤！答案是：{q['answer']}")
                    st.session_state.mistakes.append(q)
        
        if st.button("下一題 ➡️"):
            st.session_state.idx = (st.session_state.idx + 1) % len(st.session_state.quiz_data)
            st.rerun()

# (其餘複習與文法邏輯同前，為節省篇幅簡化)
