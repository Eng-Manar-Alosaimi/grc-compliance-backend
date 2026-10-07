import os
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from pdf_utils import extract_text_with_pages, chunk_by_section, find_relevant_chunks
from ai_assessor import assess_all_requirements
from analytics import compute_analytics

app = FastAPI(title="AI Compliance Checker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_requirements():
    with open("requirements.json", "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
def root():
    return {"status": "ok", "service": "AI Compliance Checker"}


@app.post("/assess")
async def assess_compliance(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    pages = extract_text_with_pages(pdf_bytes)

    if not pages:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    chunks = chunk_by_section(pages)
    requirements = load_requirements()
    results = assess_all_requirements(requirements, chunks, max_workers=5)
    analytics_results = compute_analytics(results)

    return {
        "document_name": file.filename,
        "total_pages": len(pages),
        "raw_assessments": results,
        "analytics": analytics_results
    }


@app.post("/assess/export")
async def assess_and_export(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    pages = extract_text_with_pages(pdf_bytes)

    if not pages:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    chunks = chunk_by_section(pages)
    requirements = load_requirements()
    results = assess_all_requirements(requirements, chunks, max_workers=5)
    analytics_results = compute_analytics(results)

    response_data = {
        "document_name": file.filename,
        "total_pages": len(pages),
        "raw_assessments": results,
        "analytics": analytics_results
    }

    filename = file.filename.replace(".pdf", "_assessment.json")
    formatted_json = json.dumps(response_data, indent=2, ensure_ascii=False)

    return Response(
    content=formatted_json,
    media_type="application/json",
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )