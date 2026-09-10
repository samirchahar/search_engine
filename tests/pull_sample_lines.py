# tests/pull_sample_lines.py
# Picks N random files from the corpus and prints a few distinctive
# sentences from each — use these as a starting point for exact-match
# eval queries (reword slightly so it's not a 100% verbatim copy-paste).

import sys
import os
import random
import re
sys.path.insert(0, 'src')

from extractor.extractor import extract_file

FOLDER = "data/legal_medical"
NUM_FILES = 15
SENTENCES_PER_FILE = 2
MIN_WORDS = 8
MAX_WORDS = 22

random.seed(7)  # different seed = different files than the first run

all_files = [f for f in os.listdir(FOLDER)
             if f.lower().endswith(('.pdf', '.docx', '.txt', '.pptx'))]

if len(all_files) < NUM_FILES:
    NUM_FILES = len(all_files)

sample_files = random.sample(all_files, NUM_FILES)

for fname in sample_files:
    path = os.path.join(FOLDER, fname)
    pages = extract_file(path)
    if not pages:
        continue

    full_text = " ".join(p["text"] for p in pages)
    sentences = re.split(r'(?<=[.!?])\s+', full_text)

    # keep sentences of decent length, skip headers/junk
    candidates = [
        s.strip() for s in sentences
        if MIN_WORDS <= len(s.split()) <= MAX_WORDS
        and not s.strip().isupper()
    ]

    if not candidates:
        continue

    picks = random.sample(candidates, min(SENTENCES_PER_FILE, len(candidates)))

    print(f"\n=== {fname} ===")
    for s in picks:
        print(f"  - {s}")