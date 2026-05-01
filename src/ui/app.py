# src/ui/app.py
# Desktop UI — Local Document Search Engine
# Themes: Slate & Amber (dark) / Stone & Rust (light)
# Features: cumulative indexing, file removal, score bars, larger fonts

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import sys
import os
import darkdetect
from search.metrics import MetricsTracker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from extractor.extractor import extract_file
from search.search_engine import SearchEngine


THEMES = {
    "dark": {
        "bg_60":         "#1c1f26",
        "bg_30":         "#23272f",
        "accent_10":     "#c9963a",
        "text_primary":  "#e8e2d9",
        "text_secondary":"#888888",
        "text_hint":     "#444455",
        "text_snippet":  "#666677",
        "border":        "#2e3340",
        "score_bar":     "#c9963a",
        "score_bar_bg":  "#2a2a38",
        "file_bg":       "#1e2128",
        "file_text":     "#aaaaaa",
        "remove_btn":    "#3a2a2a",
        "remove_text":   "#884444",
        "toggle_icon":   "☀",
    },
    "light": {
        "bg_60":         "#f2ede8",
        "bg_30":         "#ffffff",
        "accent_10":     "#a0522d",
        "text_primary":  "#1e1b18",
        "text_secondary":"#999999",
        "text_hint":     "#cccccc",
        "text_snippet":  "#aaaaaa",
        "border":        "#e0d9d1",
        "score_bar":     "#a0522d",
        "score_bar_bg":  "#e8e1d9",
        "file_bg":       "#f8f4f0",
        "file_text":     "#888888",
        "remove_btn":    "#f5e8e8",
        "remove_text":   "#aa4444",
        "toggle_icon":   "☾",
    }
}


def detect_system_theme() -> str:
    try:
        return "dark" if darkdetect.isDark() else "light"
    except Exception:
        return "dark"


class SearchApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_theme = detect_system_theme()

        # Master document store — never wiped, only added to or removed from
        # { filepath: [{"docid":..., "page":..., "text":...}, ...] }
        self.all_docs_by_file = {}

        self.is_indexed = False
        self.metrics = MetricsTracker()

        self.title("Local Document Search Engine")
        self.geometry("1100x720")
        self.minsize(860, 560)
        self._apply_theme()
        self._build_ui()

    # ── Theme ──────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.T = THEMES[self.current_theme]
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

    def _toggle_theme(self):
        self.current_theme = (
            "light" if self.current_theme == "dark" else "dark")
        self._apply_theme()
        self._rebuild_ui()

    def _rebuild_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self.configure(fg_color=self.T["bg_60"])
        self.after(0, self._refresh_file_list)

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self.configure(fg_color=self.T["bg_60"])

        # ── Header ──
        header = ctk.CTkFrame(
            self, fg_color=self.T["bg_30"],
            corner_radius=0, height=58)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Document Search",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=self.T["text_primary"]
        ).pack(side="left", padx=22)

        ctk.CTkButton(
            header,
            text=self.T["toggle_icon"],
            width=36, height=28,
            fg_color="transparent",
            border_width=1,
            border_color=self.T["border"],
            text_color=self.T["text_secondary"],
            hover_color=self.T["bg_60"],
            font=ctk.CTkFont(size=14),
            command=self._toggle_theme
        ).pack(side="right", padx=14)

        for label, cmd in [("+ File", self._select_file),
                           ("+ Folder", self._select_folder)]:
            ctk.CTkButton(
                header,
                text=label,
                width=84, height=28,
                fg_color="transparent",
                border_width=1,
                border_color=self.T["accent_10"],
                text_color=self.T["accent_10"],
                hover_color=self.T["bg_60"],
                font=ctk.CTkFont(size=12),
                command=cmd
            ).pack(side="right", padx=(0, 5))

        self.status_label = ctk.CTkLabel(
            header,
            text="No documents indexed — use + File or + Folder",
            font=ctk.CTkFont(size=12),
            text_color=self.T["text_hint"]
        )
        self.status_label.pack(side="left", padx=(10, 0))

        # ── Body ──
        body = ctk.CTkFrame(self, fg_color=self.T["bg_60"],
                            corner_radius=0)
        body.pack(fill="both", expand=True, side="top")

        # ── Left file panel ──
        left = ctk.CTkFrame(
            body, fg_color=self.T["bg_30"],
            corner_radius=0, width=210)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ctk.CTkLabel(
            left,
            text="Indexed Files",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.T["text_secondary"]
        ).pack(anchor="w", padx=14, pady=(14, 6))

        ctk.CTkFrame(left, fg_color=self.T["border"],
                     height=1, corner_radius=0).pack(fill="x")

        self.file_list_frame = ctk.CTkScrollableFrame(
            left,
            fg_color=self.T["bg_30"],
            scrollbar_button_color=self.T["border"],
            corner_radius=0
        )
        self.file_list_frame.pack(fill="both", expand=True)

        # ── Right results ──
        right = ctk.CTkFrame(body, fg_color=self.T["bg_60"],
                             corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        self.results_area = ctk.CTkScrollableFrame(
            right,
            fg_color=self.T["bg_60"],
            scrollbar_button_color=self.T["bg_30"],
            scrollbar_button_hover_color=self.T["border"],
            corner_radius=0
        )
        self.results_area.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.results_area,
            text="Index a file or folder above, then type a query below.",
            font=ctk.CTkFont(size=14),
            text_color=self.T["text_hint"]
        ).pack(pady=100)

        # ── Bottom search bar ──
        bottom = ctk.CTkFrame(
            self, fg_color=self.T["bg_30"],
            corner_radius=0, height=66)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self.phrase_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bottom,
            text="Phrase",
            variable=self.phrase_var,
            font=ctk.CTkFont(size=12),
            text_color=self.T["text_secondary"],
            fg_color=self.T["accent_10"],
            hover_color=self.T["bg_60"],
            border_color=self.T["border"],
            width=20
        ).pack(side="right", padx=(0, 16), pady=20)

        ctk.CTkButton(
            bottom,
            text="↑",
            width=42, height=36,
            fg_color=self.T["accent_10"],
            hover_color=self.T["accent_10"],
            text_color=self.T["bg_60"],
            font=ctk.CTkFont(size=20, weight="bold"),
            corner_radius=8,
            command=self._run_search
        ).pack(side="right", padx=(0, 8), pady=15)

        self.search_entry = ctk.CTkEntry(
            bottom,
            placeholder_text="Type a query and press Enter  ·  Shift+Enter for phrase search",
            placeholder_text_color=self.T["text_hint"],
            fg_color=self.T["bg_60"],
            border_color=self.T["border"],
            text_color=self.T["text_primary"],
            height=36,
            font=ctk.CTkFont(size=13),
            corner_radius=8
        )
        self.search_entry.pack(
            side="left", fill="x", expand=True,
            padx=(16, 8), pady=15)
        self.search_entry.bind("<Return>", lambda e: self._run_search())
        self.search_entry.bind(
            "<Shift-Return>",
            lambda e: (self.phrase_var.set(True), self._run_search()))

        # Populate file list if files already exist (after theme toggle)
        self._refresh_file_list()

    # ── File / Folder Selection ────────────────────────────────────────────

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Select documents folder")
        if not folder:
            return
        supported = ('.pdf', '.txt', '.docx', '.pptx')
        files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(supported)
        ]
        if not files:
            self._update_status("No supported files found in folder.")
            return
        self._update_status("Indexing...")
        threading.Thread(
            target=self._index_new_files,
            args=(files,), daemon=True).start()

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="Select a document",
            filetypes=[
                ("Supported files", "*.pdf *.txt *.docx *.pptx"),
                ("PDF", "*.pdf"), ("Text", "*.txt"),
                ("Word", "*.docx"), ("PowerPoint", "*.pptx"),
            ]
        )
        if not path:
            return
        self._update_status("Indexing...")
        threading.Thread(
            target=self._index_new_files,
            args=([path],), daemon=True).start()

    def _index_new_files(self, new_files: list):
        """Add new files to the existing index. Skip already-indexed files."""
        to_index = [
            f for f in new_files
            if f not in self.all_docs_by_file
        ]

        if not to_index:
            self._update_status("All selected files are already indexed.")
            return

        self.metrics.start_indexing()
        newly_added_docs = []
        total_words = 0

        for filepath in to_index:
            pages = extract_file(filepath)
            fname = os.path.basename(filepath)
            file_docs = []
            for p in pages:
                docid = f"{fname}::page{p['page']}"
                words = len(p["text"].split())
                total_words += words
                doc = {
                    "docid": docid,
                    "filepath": filepath,
                    "page": p["page"],
                    "text": p["text"]
                }
                file_docs.append(doc)
                newly_added_docs.append(doc)
            self.all_docs_by_file[filepath] = file_docs

        self._rebuild_engine()

        m = self.metrics.finish_indexing(
            files=len(to_index),
            pages=len(newly_added_docs),
            words=total_words
        )
        elapsed = m.index_time_ms
        total_files = len(self.all_docs_by_file)
        total_pages = sum(
            len(docs) for docs in self.all_docs_by_file.values())
        self._update_status(
            f"{total_pages} pages · {total_files} files · "
            f"+{len(to_index)} added in {elapsed}ms")

        self.after(0, self._refresh_file_list)

    def _rebuild_engine(self):
        """Rebuild the search engine from all currently indexed docs."""
        all_docs = []
        for docs in self.all_docs_by_file.values():
            all_docs.extend(docs)

        engine = SearchEngine()
        engine.index_documents(all_docs)
        self.engine = engine
        self.is_indexed = len(all_docs) > 0

    def _remove_file(self, filepath: str):
        """Remove a file from the index and rebuild."""
        if filepath not in self.all_docs_by_file:
            return

        fname = os.path.basename(filepath)
        confirm = messagebox.askyesno(
            "Remove file",
            f"Remove '{fname}' from the index?")
        if not confirm:
            return

        del self.all_docs_by_file[filepath]
        self._rebuild_engine()

        total_files = len(self.all_docs_by_file)
        total_pages = sum(
            len(docs) for docs in self.all_docs_by_file.values())

        if total_files == 0:
            self._update_status(
                "No documents indexed — use + File or + Folder")
        else:
            self._update_status(
                f"{total_pages} pages · {total_files} files indexed")

        self._refresh_file_list()
        self._clear_results()

    # ── File List Panel ────────────────────────────────────────────────────

    def _refresh_file_list(self):
        for w in self.file_list_frame.winfo_children():
            w.destroy()

        if not self.all_docs_by_file:
            ctk.CTkLabel(
                self.file_list_frame,
                text="No files yet.",
                font=ctk.CTkFont(size=12),
                text_color=self.T["text_hint"]
            ).pack(pady=20)
            return

        ext_icons = {
            ".pdf": "📄", ".txt": "📝",
            ".docx": "📘", ".pptx": "📊"
        }

        for filepath in self.all_docs_by_file:
            fname = os.path.basename(filepath)
            ext = os.path.splitext(fname)[1].lower()
            icon = ext_icons.get(ext, "📁")
            pages = len(self.all_docs_by_file[filepath])

            card = ctk.CTkFrame(
                self.file_list_frame,
                fg_color=self.T["file_bg"],
                corner_radius=6
            )
            card.pack(fill="x", padx=8, pady=3)

            # File name
            ctk.CTkLabel(
                card,
                text=f"{icon}  {fname}",
                font=ctk.CTkFont(size=12),
                text_color=self.T["file_text"],
                anchor="w",
                wraplength=150
            ).pack(anchor="w", padx=10, pady=(7, 1))

            # Page count + remove button row
            bottom_row = ctk.CTkFrame(card, fg_color="transparent")
            bottom_row.pack(fill="x", padx=10, pady=(0, 6))

            ctk.CTkLabel(
                bottom_row,
                text=f"{pages} page(s)",
                font=ctk.CTkFont(size=10),
                text_color=self.T["text_hint"]
            ).pack(side="left")

            # Capture filepath in closure
            fp = filepath
            ctk.CTkButton(
                bottom_row,
                text="✕ Remove",
                width=72, height=20,
                fg_color=self.T["remove_btn"],
                text_color=self.T["remove_text"],
                hover_color=self.T["remove_btn"],
                font=ctk.CTkFont(size=10),
                corner_radius=4,
                command=lambda f=fp: self._remove_file(f)
            ).pack(side="right")

    # ── Search ─────────────────────────────────────────────────────────────

    def _run_search(self):
        if not self.is_indexed:
            self._update_status("Index a file or folder first.")
            return
        query = self.search_entry.get().strip()
        if not query:
            return

        self.metrics.start_query()
        if self.phrase_var.get():
            results = self.engine.phrase_search(query)
            mode = "phrase"
        else:
            results = self.engine.search(query)
            mode = "keyword"
        qm = self.metrics.finish_query(query, mode, len(results))
        elapsed = qm.latency_ms
        self._display_results(results, mode, elapsed)

    # ── Results ────────────────────────────────────────────────────────────

    def _clear_results(self):
        self.after(0, lambda: [
            w.destroy() for w in self.results_area.winfo_children()])

    def _display_results(self, results, mode, elapsed_ms):
        self._clear_results()

        if not results:
            self.after(0, lambda: ctk.CTkLabel(
                self.results_area,
                text="No results found.",
                font=ctk.CTkFont(size=14),
                text_color=self.T["text_hint"]
            ).pack(pady=80))
            self._update_status(f"No results · {elapsed_ms}ms")
            return

        self._update_status(
            f"{len(results)} result(s) · {mode} · {elapsed_ms}ms")

        top_score = results[0]["score"] if results else 1

        self.after(0, lambda: [
            self._add_result_row(i + 1, r, top_score)
            for i, r in enumerate(results)
        ])

    def _add_result_row(self, index: int, result: dict, top_score: float):
        filename = os.path.basename(result['filepath'])
        score = result['score']

        row = ctk.CTkFrame(
            self.results_area,
            fg_color=self.T["bg_60"],
            corner_radius=0
        )
        row.pack(fill="x", padx=24, pady=0)

        ctk.CTkFrame(row, fg_color=self.T["border"],
                     height=1, corner_radius=0).pack(fill="x")

        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(fill="x", pady=12)

        # Filename + score
        top_line = ctk.CTkFrame(content, fg_color="transparent")
        top_line.pack(fill="x")

        ctk.CTkLabel(
            top_line,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.T["text_primary"] if index == 1
            else self.T["text_secondary"],
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            top_line,
            text=str(score),
            font=ctk.CTkFont(size=12),
            text_color=self.T["accent_10"] if index == 1
            else self.T["text_hint"],
            anchor="e"
        ).pack(side="right")

        # Score bar
        bar_frame = ctk.CTkFrame(content, fg_color="transparent", height=4)
        bar_frame.pack(fill="x", pady=(3, 0))
        bar_frame.pack_propagate(False)

        ctk.CTkFrame(bar_frame, fg_color=self.T["score_bar_bg"],
                     height=4, corner_radius=2).place(
            relx=0, rely=0, relwidth=1, relheight=1)

        ratio = min(score / top_score, 1.0) if top_score > 0 else 0
        ctk.CTkFrame(
            bar_frame,
            fg_color=self.T["score_bar"] if index == 1
            else self.T["border"],
            height=4, corner_radius=2
        ).place(relx=0, rely=0, relwidth=ratio, relheight=1)

        # Page info
        ctk.CTkLabel(
            content,
            text=f"Page {result['page']}",
            font=ctk.CTkFont(size=11),
            text_color=self.T["text_hint"],
            anchor="w"
        ).pack(fill="x", pady=(4, 3))

        # Snippet
        ctk.CTkLabel(
            content,
            text=result['snippet'],
            font=ctk.CTkFont(size=12),
            text_color=self.T["text_snippet"],
            anchor="w",
            wraplength=800,
            justify="left"
        ).pack(fill="x")

    # ── Utilities ──────────────────────────────────────────────────────────

    def _update_status(self, message: str):
        self.after(0, lambda: self.status_label.configure(text=message))


def launch():
    app = SearchApp()
    app.mainloop()


if __name__ == "__main__":
    launch()