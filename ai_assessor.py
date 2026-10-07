import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

FALLBACK_MODELS = [
    "gemini-3.5-flash",           # الأحدث والمتوفر حالياً
    "gemini-3.1-flash-lite",      # بديل خفيف وسريع
    "gemini-3.1-pro-preview",     # بديل قوي للتحليل المعقد
]


def build_assessment_prompt(requirement, relevant_chunks):
    chunks_text = "\n\n---\n\n".join([
        f"[Page {c['page']}]\n{c['text']}"
        for c in relevant_chunks
    ])

    prompt = f"""
You are a compliance assessment assistant. Compare a regulatory requirement against excerpts from a company document.

CRITICAL RULES:
- Base your assessment ONLY on the provided excerpts.
- If no evidence is found, return status "NO_EVIDENCE".
- Do NOT hallucinate.
- Always cite the PAGE NUMBER where evidence was found.

REGULATORY REQUIREMENT:
ID: {requirement['id']}
Text: {requirement['requirement']}
Category: {requirement['category']}
Expected Evidence: {requirement['evidence_expected']}

COMPANY DOCUMENT EXCERPTS:
{chunks_text}

Return a JSON object with EXACTLY these fields:
{{
    "requirement_id": "{requirement['id']}",
    "status": "COMPLIANT" | "PARTIAL" | "GAP" | "NO_EVIDENCE",
    "evidence": "Exact quote or 'No evidence found'",
    "page": <page_number_or_null>,
    "section": "<section heading or null>",
    "reason": "Concise explanation",
    "recommendation": "Specific action if applicable"
}}

Return ONLY the JSON object. No markdown.
"""
    return prompt


def call_gemini_with_retry(prompt, max_retries=3):
    """
    يستدعي Gemini مع:
    - Retry عند أخطاء 503/429
    - Fallback لنماذج بديلة
    - Exponential Backoff
    """
    last_error = None

    for attempt in range(max_retries):
        for model_name in FALLBACK_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text, model_name

            except Exception as e:
                error_str = str(e)
                last_error = error_str

                # أخطاء مؤقتة: 503 (Server busy) أو 429 (Rate limit)
                if "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str:
                    continue  # جرب النموذج التالي
                else:
                    raise  # خطأ دائم، ارفع الخطأ فوراً

        # انتظر قبل الجولة التالية (1s, 2s, 4s)
        wait_time = 2 ** attempt
        time.sleep(wait_time)

    raise Exception(f"All models failed after {max_retries} retries. Last error: {last_error}")


def assess_one_requirement(req, chunks):
    """
    يقيّم متطلباً واحداً. تُستدعى بشكل متوازٍ من assess_all_requirements.
    """
    from pdf_utils import find_relevant_chunks

    relevant_chunks = find_relevant_chunks(req['requirement'], chunks, top_k=3)
    if not relevant_chunks:
        relevant_chunks = chunks[:3]

    prompt = build_assessment_prompt(req, relevant_chunks)

    try:
        response_text, model_used = call_gemini_with_retry(prompt)
        response_text = response_text.strip().replace("```json", "").replace("```", "").strip()
        assessment = json.loads(response_text)
        return {**req, **assessment, "model_used": model_used}

    except json.JSONDecodeError:
        return {
            **req,
            "status": "ERROR",
            "evidence": "Failed to parse AI response",
            "page": None, "section": None,
            "reason": "JSON parsing error",
            "recommendation": None
        }
    except Exception as e:
        return {
            **req,
            "status": "ERROR",
            "evidence": f"API error: {str(e)}",
            "page": None, "section": None,
            "reason": "API call failed",
            "recommendation": None
        }


def assess_all_requirements(requirements, chunks, max_workers=5):
    """
    يقيّم كل المتطلبات بشكل متوازٍ (5 طلبات في نفس الوقت).
    يسرّع العملية من ~50 ثانية إلى ~10 ثواني.
    """
    results = [None] * len(requirements)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(assess_one_requirement, req, chunks): idx
            for idx, req in enumerate(requirements)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {
                    **requirements[idx],
                    "status": "ERROR",
                    "evidence": f"Unexpected error: {str(e)}",
                    "page": None, "section": None,
                    "reason": "Thread error",
                    "recommendation": None
                }

    return results