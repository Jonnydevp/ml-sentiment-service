# Реализован визуальный интерфейс сервиса
import streamlit as st

st.set_page_config(
    page_title="Sentiment Analysis",
    page_icon="🔍",
    layout="wide",
)

analyze_page = st.Page("pages/1_analyze.py", title="Анализ текста", icon="🔍")
history_page = st.Page("pages/2_history.py", title="История", icon="📋")
dashboard_page = st.Page("pages/3_dashboard.py", title="Дашборд", icon="📊")

nav = st.navigation([analyze_page, history_page, dashboard_page])
nav.run()
