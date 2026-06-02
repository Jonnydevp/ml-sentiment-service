# Изоляция ML-логики
import time

import structlog
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = structlog.get_logger()


class SentimentAnalyzer:
    """Инкапсулированный ML-сервис для анализа тональности текста.
    API не знает деталей реализации — только вызывает predict()."""

    def __init__(self, model_name: str, max_length: int = 512):
        self._model_name = model_name
        self._max_length = max_length
        self._model = None
        self._tokenizer = None
        self._labels = {0: "NEGATIVE", 1: "POSITIVE"}
        self._ready = False

    # Управление ресурсами
    def load(self) -> None:
        # Логирование
        start = time.time()
        logger.info("model_loading", model=self._model_name)

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name)
        self._model.eval()

        elapsed = time.time() - start
        logger.info("model_loaded", model=self._model_name, duration_s=round(elapsed, 2))
        self._ready = True

    @property
    def is_ready(self) -> bool:
        return self._ready

    def predict(self, text: str) -> dict:
        if not self._ready:
            raise RuntimeError("Модель не загружена")

        # Логирование
        start = time.time()

        # Управление ресурсами — ограничение max_length
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
            padding=True,
        )

        with torch.no_grad():
            outputs = self._model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][predicted_class].item()

        elapsed_ms = (time.time() - start) * 1000

        # Логирование
        logger.info(
            "inference_complete",
            sentiment=self._labels[predicted_class],
            confidence=round(confidence, 4),
            duration_ms=round(elapsed_ms, 2),
        )

        return {
            "sentiment": self._labels[predicted_class],
            "confidence": round(confidence, 4),
            "processing_time_ms": round(elapsed_ms, 2),
        }

    # Управление ресурсами — батчинг
    def predict_batch(self, texts: list[str]) -> list[dict]:
        if not self._ready:
            raise RuntimeError("Модель не загружена")

        start = time.time()

        inputs = self._tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
            padding=True,
        )

        with torch.no_grad():
            outputs = self._model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        elapsed_ms = (time.time() - start) * 1000

        results = []
        for i in range(len(texts)):
            predicted_class = torch.argmax(probs[i]).item()
            confidence = probs[i][predicted_class].item()
            results.append({
                "sentiment": self._labels[predicted_class],
                "confidence": round(confidence, 4),
                "processing_time_ms": round(elapsed_ms / len(texts), 2),
            })

        logger.info("batch_inference_complete", count=len(texts), duration_ms=round(elapsed_ms, 2))
        return results

    def cleanup(self) -> None:
        logger.info("model_cleanup")
        self._model = None
        self._tokenizer = None
        self._ready = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
