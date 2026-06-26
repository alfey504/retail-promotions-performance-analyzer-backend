
from services.kpi_services.incremental_uplift import get_incremental_sales_uplift, Uplift
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class IncrementalUpliftInput(BaseModel):
    promotion_id: int = Field(
        ...,
        description="The unique id of the promotion to compute incremental sales uplift for.",
    )
 
 
def _phrase(value: float, label: str) -> str:
    """'unit sales increased by 12.3%' / 'revenue decreased by 4.0%' / 'revenue
    stayed flat' -- avoids the awkward 'increased by 0.0%' for an exact-zero
    change."""
    if value > 0:
        return f"{label} increased by {value:.1f}%"
    if value < 0:
        return f"{label} decreased by {abs(value):.1f}%"
    return f"{label} stayed flat"
 
 
def _format_uplift(uplift: Uplift) -> str:
    """Converts an Uplift result into prose the agent can use directly, rather
    than handing back raw numbers it would have to interpret itself."""
    if uplift.unit_sales_uplift is None or uplift.revenue_uplift is None:
        return (
            f"Promotion {uplift.promotion_id}: the baseline period has no sales "
            f"history for the targeted SKU(s) (baseline units: {uplift.baseline_units_sold}, "
            f"baseline revenue: ${uplift.baseline_revenue:,.2f}), so a meaningful uplift "
            f"percentage can't be computed -- this usually means the promotion starts too "
            f"close to the start of the dataset for an equal-length prior period to exist. "
            f"During the promotion itself, {uplift.promotion_units_sold} units sold for "
            f"${uplift.promotion_revenue:,.2f} in revenue. Treat this promotion's performance "
            f"as unverified rather than a real lift or dud."
        )
 
    if uplift.clean_win:
        verdict = "a clean win: both unit sales and revenue improved over baseline"
    elif uplift.sales_up_revenue_down:
        verdict = (
            "a volume-up/revenue-down case: more units sold, but revenue fell -- "
            "the discount likely cost more than it earned back"
        )
    elif uplift.unit_sales_uplift <= 0 and uplift.revenue_uplift <= 0:
        verdict = "a dud: both unit sales and revenue were flat or down versus baseline"
    else:
        verdict = "a mixed result that doesn't cleanly fit a win, a dud, or a volume/revenue tradeoff"
 
    return (
        f"Promotion {uplift.promotion_id}: {_phrase(uplift.unit_sales_uplift, 'unit sales')} "
        f"versus baseline ({uplift.baseline_units_sold} -> {uplift.promotion_units_sold} units), "
        f"and {_phrase(uplift.revenue_uplift, 'revenue')} "
        f"(${uplift.baseline_revenue:,.2f} -> ${uplift.promotion_revenue:,.2f}). "
        f"This is {verdict}."
    )
 
@tool(
    "get_incremental_sales_uplift",
    args_schema=IncrementalUpliftInput,
    response_format="content_and_artifact",
)
def incremental_sales_uplift_tool(promotion_id: int):
    """Computes incremental sales uplift for a promotion: how unit sales and
    revenue during the promotion compare to an equal-length baseline period
    immediately before it started. Use this to answer whether a promotion
    actually lifted sales, whether it was a clean win, or whether it increased
    volume while losing revenue to discounting."""
    uplift = get_incremental_sales_uplift(promotion_id)
    return _format_uplift(uplift), uplift