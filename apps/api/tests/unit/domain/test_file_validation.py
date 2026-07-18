from src.domain.candidate.file_validation import detect_file_signature


def test_detects_pdf_signature() -> None:
    assert detect_file_signature(b"%PDF-1.4\n...") == "pdf"


def test_detects_docx_signature() -> None:
    assert detect_file_signature(b"PK\x03\x04rest of a zip/docx file") == "docx"


def test_rejects_unrecognized_bytes() -> None:
    assert detect_file_signature(b"just some plain text, not a document") is None


def test_rejects_empty_bytes() -> None:
    assert detect_file_signature(b"") is None


def test_extension_alone_is_not_trusted() -> None:
    # A .pdf-named upload whose content isn't actually a PDF must not pass.
    fake_pdf_bytes = b"this is definitely not a pdf despite the filename"
    assert detect_file_signature(fake_pdf_bytes) is None
