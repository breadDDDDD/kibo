"""
Vertex AI Agent Search (Discovery Engine) client.
Performs a semantic search query and returns the top-K document chunks
as plain text strings — ready to be injected into a Gemini prompt.
"""
import asyncio
import logging
import re 
from functools import lru_cache

from google.cloud import discoveryengine_v1beta as discoveryengine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities from snippet text."""
    text = re.sub(r"<[^>]+>", "", text)          
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = re.sub(r"\s{2,}", " ", text)         
    return text.strip()


@lru_cache
def _get_search_client() -> discoveryengine.SearchServiceClient:
    """Cached synchronous client — created once per process."""
    return discoveryengine.SearchServiceClient()


def _build_serving_config(settings) -> str:
    return (
        f"projects/{settings.google_cloud_project}"
        f"/locations/{settings.agent_search_location}"
        f"/collections/default_collection"
        f"/engines/{settings.agent_search_engine_id}"
        f"/servingConfigs/default_config"
    )


def _sync_search(query: str, top_k: int) -> list[dict]:
    """
    Runs a Discovery Engine search and returns a list of chunk dicts:
    [{"content": str, "document_id": str}, ...]
    This is synchronous and must be called via run_in_executor.
    """
    settings = get_settings()
    client = _get_search_client()
    serving_config = _build_serving_config(settings)

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=top_k,
        # Snippets only — compatible with Standard edition Agent Search.
        # Upgrade to Enterprise edition to unlock extractive segments/answers
        # for richer, more complete chunk text from PDFs.
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
                max_snippet_count=5,
            ),
        ),
    )

    response = client.search(request)
    chunks: list[dict] = []

    for result in response.results:
        doc = result.document
        doc_id = doc.id or doc.name

        # Collect extractive segments (preferred — full chunk text)
        derived = doc.derived_struct_data
        segments = derived.get("extractive_segments", [])
        answers = derived.get("extractive_answers", [])
        snippets = derived.get("snippets", [])

        texts = (
            [s.get("content", "") for s in segments]
            or [a.get("content", "") for a in answers]
            or [s.get("snippet", "") for s in snippets]
        )

        for text in texts:
            clean = _strip_html(text)
            if clean:
                chunks.append({"content": clean, "document_id": doc_id})

    logger.debug("Agent Search returned %d chunks for query: %s", len(chunks), query)
    return chunks


async def search_parts_catalog(query: str) -> list[dict]:
    """
    Async wrapper — offloads the blocking gRPC call to a thread executor.
    Returns list of {"content": str, "document_id": str}.
    """
    settings = get_settings()
    loop = asyncio.get_event_loop()
    chunks = await loop.run_in_executor(
        None, _sync_search, query, settings.rag_top_k
    )
    return chunks


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """Formats retrieved chunks into a clean context block for the LLM."""
    if not chunks:
        return "No relevant catalog information found."
    lines = ["=== PARTS CATALOG CONTEXT ==="]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n[Chunk {i}]\n{chunk['content']}")
    lines.append("\n=== END CONTEXT ===")
    return "\n".join(lines)