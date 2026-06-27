
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.kpi_services.kpi_calculators.post_promo_dip_calculator import PostPromoDip, get_post_promo_dip


class PostPromoDipInput(BaseModel):
    promotion_id: int = Field(
        ...,
        description="The unique id of the promotion to check for a post-promotion dip.",
    )


def _format_post_promo_dip(result: PostPromoDip) -> str:
    if result.post_period_ratio is None:
        return (
            f"Promotion {result.promotion_id}: baseline units sold were "
            f"{result.baseline_units_sold}, too low (or zero) to compute a meaningful "
            f"post-promotion ratio. {result.post_period_units_sold} units sold in the "
            f"equal-length period after the promotion."
        )

    note = (
        " This is consistent with demand being pulled forward into the promotion period "
        "rather than representing durable new demand."
        if result.pull_forward_dip else ""
    )
    return (
        f"Promotion {result.promotion_id}: in the equal-length period immediately after "
        f"it ended, {result.post_period_units_sold} units sold versus a baseline of "
        f"{result.baseline_units_sold} units ({result.post_period_ratio:.2f}x baseline)."
        f"{note}"
    )


@tool(
    "get_post_promo_dip",
    args_schema=PostPromoDipInput,
    response_format="content_and_artifact",
)
def post_promo_dip_tool(promotion_id: int):
    """Checks whether sales fell below baseline in the period immediately
    after a promotion ended, compared to the same baseline used for its
    uplift calculation. Use this to tell a genuine lift apart from demand
    that was simply pulled forward into the promotion window."""
    result = get_post_promo_dip(promotion_id)
    return _format_post_promo_dip(result), result