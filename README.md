# Local Document Intelligence System

A fully offline, air-gapped document search engine. Combines a C++ inverted
index (keyword + phrase search, TF-IDF ranking) with ChromaDB semantic
search, and generates grounded answers using a local Ollama LLM. No data
ever leaves your machine.

## Setup

1. Install Python 3.11+ and create a virtual environment:
   python -m venv venv
   venv\Scripts\activate

2. Install dependencies:
   pip install -r requirements.txt

3. Compile the C++ indexer (requires g++, e.g. via MSYS2/MinGW):
   g++ src/indexer/indexer.cpp -O2 -o src/indexer/indexer.exe

4. Install Ollama (https://ollama.com/download) and pull a model:
   ollama pull llama3.2:1b

## Usage

python main.py <folder_path>

Example:
python main.py data/documents

- Type a query for hybrid keyword + semantic search, with an AI-generated answer.
- Prefix with `phrase:` for exact phrase search, e.g. `phrase:inverted index`.
- Type `quit` to exit.

## Supported file types

PDF, TXT, DOCX (OCR and PPTX support planned).

## Architecture

- `src/extractor/` — text extraction + Pydantic path/type validation
- `src/indexer/` — C++ positional inverted index (keyword + phrase search)
- `src/search/` — Python orchestration: TF-IDF ranking, ChromaDB semantic
  search, hybrid merging, Ollama answer generation
- `main.py` — CLI entry point