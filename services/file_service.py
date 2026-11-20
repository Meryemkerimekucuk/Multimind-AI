from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def read_document_bytes(filename: str, data: bytes) -> str:
    """Extract text from TXT, PDF, or DOCX bytes."""
    name = filename.lower()

    if name.endswith(".txt"):
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("cp1254", errors="replace")

    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"[Sayfa {page_number}]\n{page_text}")
        return "\n\n".join(pages)

    if name.endswith(".docx"):
        document = Document(BytesIO(data))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                paragraphs.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(paragraphs)

    raise ValueError("Desteklenmeyen belge türü. TXT, PDF veya DOCX kullanın.")


def read_uploaded_document(uploaded_file) -> str:
    return read_document_bytes(uploaded_file.name, uploaded_file.getvalue())


def save_uploaded_file(uploaded_file, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(uploaded_file.getvalue())
    return str(destination)


def save_image_bytes(image_bytes: bytes, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image_bytes)
    return str(destination)
