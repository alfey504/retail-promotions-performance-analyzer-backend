
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.rag_services.qdrant_services import (
    PROMOTION_GUIDEBOOK_COLLECTION_NAME,
    PROMOTION_PROFILE_COLLECTION_NAME,
    search_query,
)


class SemanticSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="The natural-language question or topic to search for.",
    )
    top_k: int = Field(
        5,
        description="How many relevant excerpts to return. Defaults to 5; raise it for a broader sweep.",
        ge=1,
        le=20,
    )


def _format_search_results(texts: list[str], query: str, source: str) -> str:
    if not texts:
        return f"No relevant content found in {source} for the query: '{query}'."
    parts = [f"Found {len(texts)} relevant excerpt(s) in {source} for '{query}':"]
    for i, text in enumerate(texts, 1):
        parts.append(f"[{i}] {text}")
    return "\n\n".join(parts)


def _run_search(query: str, top_k: int, collection: str, source_label: str):
    try:
        print(f"searching vector db: {collection}")
        texts = search_query(query, top_k=top_k, collection=collection)
    except Exception as e:
        error = f"Semantic search failed ({source_label}): {e}"
        return error, None
    return _format_search_results(texts, query, source_label), texts


@tool(
    "search_promotion_profiles",
    args_schema=SemanticSearchInput,
    response_format="content_and_artifact",
)
def search_promotion_profiles_tool(query: str, top_k: int = 5):
    """Searches per-promotion profile documents (promotion_profile.pdf) by
    meaning and keyword (hybrid dense + BM25). Use this to find or recall
    details about specific past or current promotions -- e.g. finding
    promotions similar to a known case, retrieving a promotion's stated goals
    or targeting strategy, or surfacing notes/context tied to a particular
    promotion that isn't captured in the structured KPI data. Do NOT use this
    for precise numbers (uplift, revenue, stock levels) -- use the KPI tools
    for those instead."""
    return _run_search(
        query,
        top_k,
        collection=PROMOTION_PROFILE_COLLECTION_NAME,
        source_label="promotion profiles",
    )


@tool(
    "search_sales_guidebook",
    args_schema=SemanticSearchInput,
    response_format="content_and_artifact",
)
def search_sales_guidebook_tool(query: str, top_k: int = 5):
    """Searches the internal sales guidebook (sales_guidebook.md) by meaning
    and keyword (hybrid dense + BM25). Use this for definitions, formulas,
    benchmark ranges, diagnostic playbooks, and best-practice guidance on
    promotion KPIs (uplift, discount efficiency, post-promo dip, stockout
    impact, cannibalization, ROI) -- e.g. "what's a healthy pull-forward
    range" or "what should I recommend when stockouts are detected early in a
    promotion". Do NOT use this for facts about a specific promotion -- use
    search_promotion_profiles or the KPI tools for that."""
    return _run_search(
        query,
        top_k,
        collection=PROMOTION_GUIDEBOOK_COLLECTION_NAME,
        source_label="sales guidebook",
    )