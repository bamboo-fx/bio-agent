"""External tools: PubMed search, PDF ingestion."""

import httpx
from openai import OpenAI
from config import OPENAI_API_KEY, CHAT_MODEL


client = OpenAI(api_key=OPENAI_API_KEY)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def search_pubmed(query: str, max_results: int = 5) -> list[dict]:
    """Search PubMed for papers matching a query."""
    async with httpx.AsyncClient() as http:
        # Search for IDs
        search_resp = await http.get(PUBMED_SEARCH_URL, params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
        })
        search_data = search_resp.json()
        ids = search_data.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # Fetch abstracts
        fetch_resp = await http.get(PUBMED_FETCH_URL, params={
            "db": "pubmed",
            "id": ",".join(ids),
            "rettype": "abstract",
            "retmode": "xml",
        })

        # Simple extraction (XML parsing kept minimal)
        results = []
        for pmid in ids:
            results.append({
                "pmid": pmid,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        return results


def summarize_text(text: str, instruction: str = "Summarize this text concisely") -> str:
    """Use LLM to summarize a piece of text."""
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": text[:8000]},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    return resp.choices[0].message.content
