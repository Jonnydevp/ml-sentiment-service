# Визуальная репрезентация — графики на веб-странице
import os

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")

st.title("Дашборд аналитики")


@st.fragment(run_every=5)
def live_dashboard():
    """Динамическое обновление дашборда каждые 5 секунд."""
    try:
        stats_resp = httpx.get(f"{API_URL}/api/stats", timeout=5.0)
        history_resp = httpx.get(
            f"{API_URL}/api/history", params={"page": 1, "per_page": 100}, timeout=5.0
        )

        if stats_resp.status_code == 200:
            stats = stats_resp.json()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Всего анализов", stats["total_analyses"])
            col2.metric("Positive", stats["positive_count"])
            col3.metric("Negative", stats["negative_count"])
            col4.metric("Ср. время (мс)", f"{stats['avg_processing_time_ms']:.1f}")

            if stats["total_analyses"] > 0:
                sentiment_data = pd.DataFrame({
                    "Тональность": ["POSITIVE", "NEGATIVE"],
                    "Количество": [stats["positive_count"], stats["negative_count"]],
                })
                fig_pie = px.pie(
                    sentiment_data,
                    values="Количество",
                    names="Тональность",
                    title="Распределение тональности",
                    color="Тональность",
                    color_discrete_map={"POSITIVE": "#00CC96", "NEGATIVE": "#EF553B"},
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        if history_resp.status_code == 200:
            items = history_resp.json()["items"]
            if items:
                df = pd.DataFrame(items)
                df["created_at"] = pd.to_datetime(df["created_at"])

                fig_conf = px.histogram(
                    df,
                    x="confidence",
                    nbins=20,
                    title="Распределение уверенности модели",
                    color="sentiment",
                    color_discrete_map={"POSITIVE": "#00CC96", "NEGATIVE": "#EF553B"},
                )
                st.plotly_chart(fig_conf, use_container_width=True)

                fig_time = px.line(
                    df.sort_values("created_at"),
                    x="created_at",
                    y="processing_time_ms",
                    title="Время обработки запросов",
                    markers=True,
                )
                st.plotly_chart(fig_time, use_container_width=True)

    except httpx.ConnectError:
        # Обработка сбоев
        st.error("Не удалось подключиться к серверу. Сервис временно недоступен.")
    except httpx.TimeoutException:
        st.warning("Сервер не отвечает.")


# Изоляция в сети — UI не ходит в БД, только к API
live_dashboard()
