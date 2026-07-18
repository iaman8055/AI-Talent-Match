# Pure magic-byte signature checks — no python-magic/libmagic dependency (painful on Windows),
# and no reliance on client-declared content-type/extension, which is trivially spoofable.

_PDF_SIGNATURE = b"%PDF-"
_ZIP_SIGNATURE = b"PK\x03\x04"  # DOCX is a ZIP container (OOXML)

ALLOWED_RESUME_TYPES = frozenset({"pdf", "docx"})


def detect_file_signature(data: bytes) -> str | None:
    """Returns "pdf", "docx", or None if the bytes don't match either signature."""
    if data.startswith(_PDF_SIGNATURE):
        return "pdf"
    if data.startswith(_ZIP_SIGNATURE):
        return "docx"
    return None
