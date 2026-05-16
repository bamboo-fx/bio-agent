"""Document ingestion: PDFs, text files, papers."""

from pathlib import Path
from PyPDF2 import PdfReader
from openai import OpenAI

from config import OPENAI_API_KEY, CHAT_MODEL
from agent.memory import MemoryStore


client = OpenAI(api_key=OPENAI_API_KEY)

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def extract_pdf_text(file_path: str) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def extract_key_facts(text: str) -> list[dict]:
    """Use LLM to extract key facts from a document chunk."""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """Extract key biological facts from this text. Return a JSON array of objects:
[{"content": "fact text", "category": "molecular_biology|genetics|ecology|biochemistry|evolution|methods|general"}]
Only include specific, factual claims. Max 5 facts per chunk.""",
            },
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000,
    )
    import json
    try:
        result = json.loads(resp.choices[0].message.content)
        # Handle both {"facts": [...]} and direct [...] formats
        if isinstance(result, list):
            return result
        return result.get("facts", [])
    except Exception:
        return []


def ingest_document(file_path: str, memory: MemoryStore) -> dict:
    """Ingest a document into the knowledge base."""
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = extract_pdf_text(file_path)
    elif path.suffix.lower() in (".txt", ".md"):
        text = path.read_text()
    else:
        return {"error": f"Unsupported file type: {path.suffix}"}

    chunks = chunk_text(text)
    total_facts = 0

    for chunk in chunks:
        facts = extract_key_facts(chunk)
        for fact in facts:
            memory.store_fact(
                content=fact["content"],
                category=fact.get("category", "general"),
                source=path.name,
            )
            total_facts += 1

    return {
        "file": path.name,
        "chunks_processed": len(chunks),
        "facts_extracted": total_facts,
    }
