
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.kpi_services.kpi_db.get_kpis import DiscountEfficiency, get_discount_efficiency


class DiscountEfficiencyInput(BaseModel):
    promotion_id: int = Field(
        ...,
        description="The unique id of the promotion to compute discount efficiency for.",
    )


def _format_discount_efficiency(result: DiscountEfficiency) -> str:
    if result.discount_efficiency_ratio is None:
        return (
            f"Promotion {result.promotion_id}: no discount cost was recorded (total discount "
            f"given: ${result.total_discount_given:,.2f}), so a discount efficiency ratio "
            f"can't be computed."
        )

    if result.discount_efficiency_ratio > 1:
        verdict = "the promotion more than paid for its own discount in incremental revenue"
    elif result.discount_efficiency_ratio >= 0:
        verdict = "the incremental revenue did not fully cover the cost of the discount"
    else:
        verdict = "revenue actually fell versus baseline, so the discount produced no incremental revenue at all"

    change_word = "a gain of" if result.incremental_revenue >= 0 else "a loss of"
    return (
        f"Promotion {result.promotion_id}: ${result.total_discount_given:,.2f} in discounts "
        f"were given, producing {change_word} ${abs(result.incremental_revenue):,.2f} in "
        f"incremental revenue versus baseline (${result.baseline_revenue:,.2f} -> "
        f"${result.promotion_revenue:,.2f}). That's a discount efficiency ratio of "
        f"{result.discount_efficiency_ratio:.2f}x -- {verdict}."
    )


@tool(
    "get_discount_efficiency",
    args_schema=DiscountEfficiencyInput,
    response_format="content_and_artifact",
)
def discount_efficiency_tool(promotion_id: int):
    """Computes how many dollars of incremental revenue a promotion generated
    per dollar of discount given away. Use this to rank or compare promotions
    by cost-effectiveness, not just by whether they showed a lift -- a
    promotion can have positive uplift and still be a poor use of discount
    budget."""
    result = get_discount_efficiency(promotion_id)
    return _format_discount_efficiency(result), result