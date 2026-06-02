# Слабая связность — UI общается с бэкендом только по REST API
import os
import time

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000")

st.title("Анализ тональности текста")
st.markdown("Введите текст, и ML-модель определит его тональность (POSITIVE/NEGATIVE).")

text_input = st.text_area(
    "Текст для анализа",
    height=150,
    max_chars=5000,
    placeholder="Enter your text here...",
)

confidence_threshold = st.slider(
    "Порог уверенности",
    min_value=0.0,
    max_value=1.0,
    value=0.5,
    step=0.05,
)

col1, col2 = st.columns(2)

with col1:
    sync_btn = st.button("Анализировать (синхронно)", type="primary", use_container_width=True)

with col2:
    async_btn = st.button("Анализировать (асинхронно)", use_container_width=True)

if sync_btn and text_input:
    # UX асинхронности — спиннер
    with st.spinner("Анализируем текст..."):
        try:
            response = httpx.post(
                f"{API_URL}/api/analyze",
                json={"text": text_input, "confidence_threshold": confidence_threshold},
                timeout=60.0,
            )
            if response.status_code == 200:
                data = response.json()
                sentiment = data["sentiment"]
                confidence = data["confidence"]

                if sentiment == "POSITIVE":
                    st.success(f"Результат: {sentiment}")
                else:
                    st.error(f"Результат: {sentiment}")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Тональность", sentiment)
                col_b.metric("Уверенность", f"{confidence:.1%}")
                col_c.metric("Время (мс)", f"{data['processing_time_ms']:.1f}")

                st.json(data)
            elif response.status_code == 422:
                st.warning("Невалидные данные. Проверьте введённый текст.")
            elif response.status_code == 503:
                # Обработка сбоев
                st.error("Сервис временно недоступен. ML-модель ещё загружается.")
            else:
                st.error(f"Ошибка сервера: {response.status_code}")
        except httpx.ConnectError:
            # Обработка сбоев
            st.error("Не удалось подключиться к серверу. Сервис временно недоступен.")
        except httpx.TimeoutException:
            st.error("Превышено время ожидания ответа.")

if async_btn and text_input:
    # UX асинхронности — progress bar и polling
    try:
        response = httpx.post(
            f"{API_URL}/api/analyze/async",
            json={"text": text_input, "confidence_threshold": confidence_threshold},
            timeout=10.0,
        )
        if response.status_code == 202:
            task_data = response.json()
            task_id = task_data["task_id"]
            st.info(f"Задача принята. ID: `{task_id}`")

            progress_bar = st.progress(0, text="Ожидание результата...")
            status_placeholder = st.empty()

            for i in range(60):
                time.sleep(1)
                progress_bar.progress(min((i + 1) * 5, 100), text="Обработка...")

                status_resp = httpx.get(f"{API_URL}/api/task/{task_id}", timeout=5.0)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()

                    if status_data["status"] == "SUCCESS":
                        progress_bar.progress(100, text="Готово!")
                        result = status_data["result"]

                        if result["sentiment"] == "POSITIVE":
                            st.success(f"Результат: {result['sentiment']}")
                        else:
                            st.error(f"Результат: {result['sentiment']}")

                        st.json(result)
                        break
                    elif status_data["status"] == "FAILURE":
                        progress_bar.empty()
                        st.error(f"Ошибка выполнения: {status_data.get('error', 'Неизвестная ошибка')}")
                        break
            else:
                progress_bar.empty()
                st.warning("Превышено время ожидания. Проверьте статус позже.")
        else:
            st.error(f"Ошибка: {response.status_code}")
    except httpx.ConnectError:
        # Обработка сбоев
        st.error("Не удалось подключиться к серверу. Сервис временно недоступен.")

if not text_input and (sync_btn or async_btn):
    st.warning("Введите текст для анализа.")
