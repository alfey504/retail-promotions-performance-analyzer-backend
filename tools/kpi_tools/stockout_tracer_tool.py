from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.kpi_services.stockout_tracer import StockoutTrace, get_stockout_inventory_trace


class StockoutTracerInput(BaseModel):
    promotion_id: int = Field(
        ...,
        description="The unique id of the promotion to trace inventory for.",
    )


def _format_stockout_trace(trace: StockoutTrace) -> str:
    if not trace.sku_traces:
        return f"Promotion {trace.promotion_id}: no targeted SKUs found to trace inventory for."

    stocked_out = [t for t in trace.sku_traces if t.stockout]
    routine = [t for t in trace.sku_traces if not t.stockout]
    parts = []

    if stocked_out:
        sentences = []
        for t in stocked_out:
            restock = t.next_restock_date.isoformat() if t.next_restock_date else "an unrecorded date"
            sentences.append(
                f"SKU {t.sku_id} opened with {t.opening_stock} units, sold {t.units_sold} during "
                f"the window, and stocked out on {t.stockout_date.isoformat()} (next restock: "
                f"{restock}, an estimated {t.missed_units_estimate} unit(s) likely missed)"
            )
        parts.append("; ".join(sentences) + ".")

    if routine:
        if len(routine) <= 2:
            sentences = [
                f"SKU {t.sku_id} opened with {t.opening_stock} units, sold {t.units_sold}, and "
                f"closed with {t.closing_stock} on hand" for t in routine
            ]
            parts.append("; ".join(sentences) + " (no stockout).")
        else:
            openings = [t.opening_stock for t in routine]
            closings = [t.closing_stock for t in routine]
            total_sold = sum(t.units_sold for t in routine)
            parts.append(
                f"The remaining {len(routine)} targeted SKU(s) opened with {min(openings)}-"
                f"{max(openings)} units on hand, sold {total_sold} units between them, and closed "
                f"with {min(closings)}-{max(closings)} units; none of them stocked out."
            )

    summary = f"Promotion {trace.promotion_id} "
    summary += "experienced at least one stockout" if trace.any_stockout else "did not stock out on any targeted SKU"
    summary += (
        f", with an estimated {trace.total_missed_units_estimate} total unit(s) missed as a result. "
        if trace.any_stockout else ". "
    )
    return summary + " ".join(parts)


@tool(
    "get_stockout_inventory_trace",
    args_schema=StockoutTracerInput,
    response_format="content_and_artifact",
)
def stockout_inventory_trace_tool(promotion_id: int):
    """Traces opening-to-closing stock for every SKU targeted by a promotion
    across its active window, flags whether any SKU ran out of stock before
    the window ended, and estimates how many additional units were likely
    missed as a result. Use this when asked whether a promotion's results
    were limited by supply, or whether it 'would have done better' with more
    stock."""
    trace = get_stockout_inventory_trace(promotion_id)
    return _format_stockout_trace(trace), trace