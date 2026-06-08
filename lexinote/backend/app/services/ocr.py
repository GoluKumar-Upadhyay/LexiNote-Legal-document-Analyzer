from __future__ import annotations

from typing import Any

from app.core.config import settings

try:
    from google.cloud import vision_v1 as vision
except Exception:  # pragma: no cover
    vision = None


class VisionOCR:
    def __init__(self) -> None:
        self._client = None
        self._error = None

    def available(self) -> bool:
        return bool(vision and settings.prepare_google_credentials())

    def client(self) -> Any:
        if self._client is not None:
            return self._client
        if self._error is not None:
            raise RuntimeError(self._error)
        if not self.available():
            self._error = "Google Vision OCR is not configured."
            raise RuntimeError(self._error)
        self._client = vision.ImageAnnotatorClient()
        return self._client

    def detect(self, image_bytes: bytes) -> str:
        client = self.client()
        image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=image)
        return (response.full_text_annotation.text or "").strip()


ocr = VisionOCR()
