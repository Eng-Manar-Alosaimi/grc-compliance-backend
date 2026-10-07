import pymupdf as fitz
import re

def extract_text_with_pages(pdf_bytes):
    """
    يستخرج النص من PDF مع الحفاظ على رقم الصفحة.
    Returns: list of dicts [{"page": 1, "text": "..."}, ...]
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if text:
            pages.append({"page": page_num, "text": text})
    return pages


def chunk_by_section(pages, max_chunk_size=800):
    """
    يقسم كل صفحة إلى chunks مع الاحتفاظ برقم الصفحة.
    """
    chunks = []
    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]
        
        paragraphs = text.split("\n\n")
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append({
                        "page": page_num,
                        "text": current_chunk.strip()
                    })
                current_chunk = para + "\n\n"
        
        if current_chunk.strip():
            chunks.append({
                "page": page_num,
                "text": current_chunk.strip()
            })
    
    return chunks


def find_relevant_chunks(requirement_text, chunks, top_k=3):
    """
    يجد أكثر الأجزاء صلة بالمتطلب بناءً على تطابق الكلمات المفتاحية.
    """
    keywords = set(re.findall(r'\b[a-zA-Z]{4,}\b', requirement_text.lower()))
    stopwords = {
        "shall", "must", "with", "that", "this", "from",
        "have", "been", "their", "which", "institution",
        "established", "establish", "defined", "clear"
    }
    keywords -= stopwords
    
    scored = []
    for chunk in chunks:
        chunk_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', chunk["text"].lower()))
        overlap = len(keywords & chunk_words)
        if overlap > 0:
            scored.append({**chunk, "relevance_score": overlap})
    
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]