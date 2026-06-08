from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import BASE_DIR, settings
from app.core.logging import configure_logging
from app.schemas.models import MindMapRequest
from app.services.analysis import CATEGORY_RULES, classify_document, extract_text, generate_mindmap, summarize_document
from app.services.llm import llm
from app.services.ocr import ocr
from app.services.video import GENERATED_DIR, VIDEOS_DIR, generate_video, video_runtime_available

configure_logging()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-MS"] = str(int((time.perf_counter() - started) * 1000))
    return response


@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "providers": llm.available_providers(),
        "ocr": {"google_vision": ocr.available()},
        "video_enabled": video_runtime_available(),
        "structure": {"root": str(BASE_DIR), "generated": str(GENERATED_DIR)},
    }


@app.get("/api/active")
async def active():
    return {"status": "active"}


@app.get("/api/files/videos/{filename}")
async def serve_video(filename: str):
    target = VIDEOS_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(target)


@app.post("/api/uploads")
async def uploads(category: str = Form(...), file: UploadFile = File(...)):
    selected_category = category.strip().lower()
    if selected_category not in CATEGORY_RULES:
        raise HTTPException(status_code=400, detail="Invalid category")

    file_bytes = await file.read()
    text, warnings = extract_text(file_bytes, file.filename or "uploaded-file")
    classification, provider = classify_document(text, selected_category)
    classification["extracted_text"] = text
    classification["_meta"] = {"provider_used": provider, "warnings": warnings}
    return classification


@app.post("/api/summarize")
async def summarize(category: str = Form(...), document_text: str = Form(...)):
    selected_category = category.strip().lower()
    if selected_category not in CATEGORY_RULES:
        selected_category = "citizen"
    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Empty document_text")
    return summarize_document(selected_category, document_text)


@app.post("/api/generate_mindmap")
async def generate_mindmap_route(payload: MindMapRequest):
    category = payload.category.strip().lower()
    if category not in CATEGORY_RULES:
        category = "citizen"
    return generate_mindmap(payload.summary_json, category)


@app.post("/api/generate_video")
async def generate_video_route(
    summary_text: str = Form(...),
    category: str = Form("citizen"),
    language: str = Form("en"),
):
    selected_category = category.strip().lower()
    if selected_category not in CATEGORY_RULES:
        selected_category = "citizen"
    if not summary_text.strip():
        raise HTTPException(status_code=400, detail="summary_text is required")
    return generate_video(summary_text, selected_category, language.strip().lower())
