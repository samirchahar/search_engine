# src/extractor/file_validator.py
# Validates a file path before it reaches any parser.
# Blocks unsupported extensions, missing files, and path traversal.

import os
from pydantic import BaseModel, field_validator

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx"}


class FileRequest(BaseModel):
    filepath: str

    @field_validator("filepath")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("path traversal sequence detected")
        ext = os.path.splitext(v)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"unsupported file type: {ext}")
        real = os.path.realpath(v)
        if not os.path.isfile(real):
            raise ValueError(f"file not found: {real}")
        return real