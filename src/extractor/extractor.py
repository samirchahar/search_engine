# src/extractor/extractor.py
# Extracts text from PDF, TXT, DOCX. (OCR/PPTX: phase 2)

import fitz
from docx import Document


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    words = text.split()
    if not words:
        return []
    results, start, page_num = [], 0, 1
    while start < len(words):
        end = min(start + chunk_size, len(words))
        results.append({"page": page_num, "text": " ".join(words[start:end])})
        start += chunk_size - overlap
        page_num += 1
    return results


def extract_pdf(filepath: str) -> list[dict]:
    results = []
    doc = fitz.open(filepath)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            results.append({"page": page_num, "text": text})
    doc.close()
    return results


def extract_txt(filepath: str) -> list[dict]:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return chunk_text(text) if text.strip() else []


def extract_docx(filepath: str) -> list[dict]:
    doc = Document(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        return []
    return chunk_text(" ".join(paragraphs))


def extract_file(filepath: str) -> list[dict]:
    fp = filepath.lower()
    if fp.endswith(".pdf"):
        return extract_pdf(filepath)
    elif fp.endswith(".txt"):
        return extract_txt(filepath)
    elif fp.endswith(".docx"):
        return extract_docx(filepath)
    print(f"Unsupported file type: {filepath}")
    return []