
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.kpi_services.kpi_db.get_kpis import RedemptionDemographics, get_redemption_demographics


class RedemptionDemographicsInput(BaseModel):
    promotion_id: int = Field(
        ...,
        description="The unique id of the promotion to profile redemption demographics for.",
    )


def _format_redemption_demographics(result: RedemptionDemographics) -> str:
    if result.redemption_count == 0:
        return f"Promotion {result.promotion_id}: no redemptions recorded, so no demographic profile is available."

    if result.under_25_share is None or result.customer_base_under_25_share is None:
        return (
            f"Promotion {result.promotion_id}: {result.redemption_count} redemption(s) recorded, "
            f"but customer-base demographics could not be computed for comparison."
        )

    base_pct = result.customer_base_under_25_share * 100
    if result.over_indexed_under_25:
        note = (
            f" This is notably higher than the customer base's overall under-25 share of "
            f"{base_pct:.0f}%, suggesting this promotion over-indexed with younger customers."
        )
    else:
        note = f" This is close to the customer base's overall under-25 share of {base_pct:.0f}%."

    return (
        f"Promotion {result.promotion_id}: {result.redemption_count} redemption(s), of which "
        f"{result.under_25_count} ({result.under_25_share*100:.0f}%) were customers under 25."
        f"{note}"
    )


@tool(
    "get_redemption_demographics",
    args_schema=RedemptionDemographicsInput,
    response_format="content_and_artifact",
)
def redemption_demographics_tool(promotion_id: int):
    """Profiles who actually redeemed a promotion by age, compared against
    the under-25 share of the overall customer base. Use this to answer
    whether a promotion skewed toward a particular age group rather than
    redeeming roughly in line with the customer base as a whole."""
    result = get_redemption_demographics(promotion_id)
    return _format_redemption_demographics(result), result