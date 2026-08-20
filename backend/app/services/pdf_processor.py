import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text page by page from PDF"""
    pages = []
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page": page_num, "text": text.strip()})
    return pages

def chunk_text(pages: list[dict], chunk_size=800, overlap=150) -> list[dict]:
    """Split pages into overlapping chunks for RAG"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = []
    for page_data in pages:
        splits = splitter.split_text(page_data["text"])
        for i, chunk in enumerate(splits):
            chunks.append({
                "text": chunk,
                "page": page_data["page"],
                "chunk_index": i
            })
    return chunks
