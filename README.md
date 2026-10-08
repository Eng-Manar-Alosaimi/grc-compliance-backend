# GRC Compliance Backend API

A FastAPI backend that assesses PDF documents against SAMA Key Principles using Google Gemini.

## Live API
https://grc-compliance-backend.vercel.app/docs

## Architecture
PDF → Text Extraction → Chunking → Relevant Matching → Gemini Assessment → Pandas Analytics → Structured JSON

## Tech Stack
FastAPI, Python, Google Gemini, Pandas, PyMuPDF

## Endpoints
- `POST /assess` — Assess a PDF and return structured findings
- `POST /assess/export` — Same, but returns downloadable JSON

## Setup
1. Clone the repo
2. `pip install -r requirements.txt`
3. Create `.env` with `GEMINI_API_KEY=your_key`
4. `uvicorn main:app --reload`

## Note
This is a working prototype (MVP), not production-ready.
