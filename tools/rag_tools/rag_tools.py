from langchain_core.tools import tool
from pydantic import BaseModel, Field
 
from services.rag_services.qdrant_services import search_query
 
 
class SemanticSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The natural-language question or topic to search the promotion corpus for.",
    )
    top_k: int = Field(
        5,
        description="How many relevant excerpts to return. Defaults to 5; raise it for a broader sweep.",
        ge=1,
        le=20,
    )
 
 
def _format_search_results(texts: list[str], query: str) -> str:
    if not texts:
        return f"No relevant content found for the query: '{query}'."
    parts = [f"Found {len(texts)} relevant excerpt(s) for '{query}':"]
    for i, text in enumerate(texts, 1):
        parts.append(f"[{i}] {text}")
    return "\n\n".join(parts)
 
 
@tool(
    "search_promotion_content",
    args_schema=SemanticSearchInput,
    response_format="content_and_artifact",
)
def semantic_search_tool(query: str, top_k: int = 5):
    """Searches the promotion corpus by meaning and keyword (hybrid dense +
    BM25), returning the most relevant text excerpts. Use this for open-ended
    or exploratory questions a fixed calculation can't answer -- e.g. finding
    promotions similar to a known case, or promotions discussing a particular
    pattern. Do NOT use this for precise numbers (uplift, revenue, stock
    levels) -- use the KPI tools for those instead."""
    try:
        print("searching vecotr db")
        texts = search_query(query, top_k=top_k)
    except Exception as e:
        error = f"Semantic search failed: {e}"
        return error, None
    return _format_search_results(texts, query), texts
 