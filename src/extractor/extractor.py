# src/extractor/extractor.py
# Extracts text from PDF, TXT, DOCX. (OCR/PPTX: phase 2)

import fitz
from docx import Document
import pytesseract
from PIL import Image
import io
from pptx import Presentation

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from pydantic import ValidationError
from extractor.file_validator import FileRequest


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
    needs_ocr = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            results.append({"page": page_num, "text": text})
        else:
            needs_ocr.append(page_num)

    if needs_ocr:
        print(f"  Running OCR on {len(needs_ocr)} scanned page(s)...")
        for page_num in needs_ocr:
            page = doc[page_num - 1]
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image)
            if text.strip():
                results.append({"page": page_num, "text": text})

    doc.close()
    results.sort(key=lambda x: x["page"])
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

def extract_pptx(filepath: str) -> list[dict]:
    prs = Presentation(filepath)
    results = []
    for slide_num, slide in enumerate(prs.slides, start=1):
        texts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                texts.append(shape.text.strip())
        if texts:
            results.append({"page": slide_num, "text": " ".join(texts)})
    return results

def extract_file(filepath: str) -> list[dict]:
    try:
        filepath = FileRequest(filepath=filepath).filepath
    except ValidationError as e:
        print(f"Rejected: {filepath} — {e.errors()[0]['msg']}")
        return []

    if filepath.endswith(".pdf"):
        return extract_pdf(filepath)
    elif filepath.endswith(".txt"):
        return extract_txt(filepath)
    elif filepath.endswith(".docx"):
        return extract_docx(filepath)
    elif filepath.endswith(".pptx"):
        return extract_pptx(filepath)
    return []