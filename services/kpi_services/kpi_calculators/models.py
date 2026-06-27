from datetime import date

from pydantic import BaseModel


class Uplift(BaseModel):
    promotion_id: int
    baseline_units_sold: int
    promotion_units_sold: int
    baseline_revenue: float
    promotion_revenue: float
    unit_sales_uplift: float
    revenue_uplift: float
    sales_up_revenue_down: bool
    clean_win: bool


class DiscountEfficiency(BaseModel):
    promotion_id: int
    baseline_revenue: float
    promotion_revenue: float
    incremental_revenue: float
    total_discount_given: float
    discount_efficiency_ratio: float | None


class PostPromoDip(BaseModel):
    promotion_id: int
    baseline_units_sold: int
    post_period_units_sold: int
    post_period_ratio: float | None
    pull_forward_dip: bool


class RedemptionDemographics(BaseModel):
    promotion_id: int
    redemption_count: int
    under_25_count: int
    under_25_share: float | None
    customer_base_under_25_share: float | None
    over_indexed_under_25: bool


class SkuInventoryTrace(BaseModel):
    sku_id: int
    opening_stock: int
    units_sold: int
    closing_stock: int
    stockout: bool
    stockout_date: date | None
    next_restock_date: date | None
    missed_units_estimate: float


class StockoutTrace(BaseModel):
    promotion_id: int
    any_stockout: bool
    total_missed_units_estimate: float
    sku_traces: list[SkuInventoryTrace]