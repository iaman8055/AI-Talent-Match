import io

import pdfplumber
from docx import Document


class DocumentTextExtractor:
    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        if file_type == "pdf":
            return self._extract_pdf(file_bytes)
        if file_type == "docx":
            return self._extract_docx(file_bytes)
        raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_bytes: bytes) -> str:
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_docx(self, file_bytes: bytes) -> str:
        document = Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
