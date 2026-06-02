# Слабая связность — общение только по REST API
import os

import httpx
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")

st.title("История анализов")

page = st.number_input("Страница", min_value=1, value=1)
per_page = st.selectbox("Записей на странице", [10, 20, 50], index=1)

# UX асинхронности
with st.spinner("Загрузка истории..."):
    try:
        response = httpx.get(
            f"{API_URL}/api/history",
            params={"page": page, "per_page": per_page},
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            items = data["items"]
            total = data["total"]

            st.info(f"Всего записей: {total}")

            if items:
                df = pd.DataFrame(items)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df = df[["id", "text", "sentiment", "confidence", "processing_time_ms", "created_at"]]
                df.columns = ["ID", "Текст", "Тональность", "Уверенность", "Время (мс)", "Дата"]

                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "Текст": st.column_config.TextColumn(width="large"),
                        "Уверенность": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f"),
                    },
                )

                total_pages = (total + per_page - 1) // per_page
                st.caption(f"Страница {page} из {total_pages}")
            else:
                st.info("История пуста. Проведите первый анализ!")
        elif response.status_code == 503:
            # Обработка сбоев
            st.error("Сервис временно недоступен.")
        else:
            st.error(f"Ошибка: {response.status_code}")
    except httpx.ConnectError:
        # Обработка сбоев
        st.error("Не удалось подключиться к серверу. Сервис временно недоступен.")
    except httpx.TimeoutException:
        st.error("Превышено время ожидания.")
