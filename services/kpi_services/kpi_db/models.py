from __future__ import annotations

from datetime import date

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db_services.session import Base 

from services.kpi_services.kpi_calculators.uplift_calculator import Uplift
from services.kpi_services.kpi_calculators.discount_efficiency_calculator import DiscountEfficiency
from services.kpi_services.kpi_calculators.post_promo_dip_calculator import PostPromoDip
from services.kpi_services.kpi_calculators.redemption_demographics_calculator import RedemptionDemographics
from services.kpi_services.kpi_calculators.stockout_calculator import StockoutTrace, SkuInventoryTrace


class UpliftResult(Base):
    __tablename__ = "uplift_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), index=True)
    baseline_units_sold: Mapped[int] = mapped_column()
    promotion_units_sold: Mapped[int] = mapped_column()
    baseline_revenue: Mapped[float] = mapped_column(Numeric(10, 2))
    promotion_revenue: Mapped[float] = mapped_column(Numeric(10, 2))
    unit_sales_uplift: Mapped[float] = mapped_column()
    revenue_uplift: Mapped[float] = mapped_column()
    sales_up_revenue_down: Mapped[bool] = mapped_column()
    clean_win: Mapped[bool] = mapped_column()


def uplift_to_orm(u: Uplift) -> UpliftResult:
    return UpliftResult(
        promotion_id=u.promotion_id,
        baseline_units_sold=u.baseline_units_sold,
        promotion_units_sold=u.promotion_units_sold,
        baseline_revenue=u.baseline_revenue,
        promotion_revenue=u.promotion_revenue,
        unit_sales_uplift=u.unit_sales_uplift,
        revenue_uplift=u.revenue_uplift,
        sales_up_revenue_down=u.sales_up_revenue_down,
        clean_win=u.clean_win,
    )


def uplift_from_orm(o: UpliftResult) -> Uplift:
    return Uplift(
        promotion_id=o.promotion_id,
        baseline_units_sold=o.baseline_units_sold,
        promotion_units_sold=o.promotion_units_sold,
        baseline_revenue=o.baseline_revenue,
        promotion_revenue=o.promotion_revenue,
        unit_sales_uplift=o.unit_sales_uplift,
        revenue_uplift=o.revenue_uplift,
        sales_up_revenue_down=o.sales_up_revenue_down,
        clean_win=o.clean_win,
    )



class DiscountEfficiencyResult(Base):
    __tablename__ = "discount_efficiency_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), index=True)
    baseline_revenue: Mapped[float] = mapped_column(Numeric(10, 2))
    promotion_revenue: Mapped[float] = mapped_column(Numeric(10, 2))
    incremental_revenue: Mapped[float] = mapped_column(Numeric(10, 2))
    total_discount_given: Mapped[float] = mapped_column(Numeric(10, 2))
    discount_efficiency_ratio: Mapped[float] = mapped_column()


def discount_efficiency_to_orm(d: DiscountEfficiency) -> DiscountEfficiencyResult:
    return DiscountEfficiencyResult(
        promotion_id=d.promotion_id,
        baseline_revenue=d.baseline_revenue,
        promotion_revenue=d.promotion_revenue,
        incremental_revenue=d.incremental_revenue,
        total_discount_given=d.total_discount_given,
        discount_efficiency_ratio=d.discount_efficiency_ratio,
    )


def discount_efficiency_from_orm(o: DiscountEfficiencyResult) -> DiscountEfficiency:
    return DiscountEfficiency(
        promotion_id=o.promotion_id,
        baseline_revenue=o.baseline_revenue,
        promotion_revenue=o.promotion_revenue,
        incremental_revenue=o.incremental_revenue,
        total_discount_given=o.total_discount_given,
        discount_efficiency_ratio=o.discount_efficiency_ratio,
    )



class PostPromoDipResult(Base):
    __tablename__ = "post_promo_dip_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), index=True)
    baseline_units_sold: Mapped[int] = mapped_column()
    post_period_units_sold: Mapped[int] = mapped_column()
    post_period_ratio: Mapped[float] = mapped_column()
    pull_forward_dip: Mapped[bool] = mapped_column()


def post_promo_dip_to_orm(p: PostPromoDip) -> PostPromoDipResult:
    return PostPromoDipResult(
        promotion_id=p.promotion_id,
        baseline_units_sold=p.baseline_units_sold,
        post_period_units_sold=p.post_period_units_sold,
        post_period_ratio=p.post_period_ratio,
        pull_forward_dip=p.pull_forward_dip,
    )


def post_promo_dip_from_orm(o: PostPromoDipResult) -> PostPromoDip:
    return PostPromoDip(
        promotion_id=o.promotion_id,
        baseline_units_sold=o.baseline_units_sold,
        post_period_units_sold=o.post_period_units_sold,
        post_period_ratio=o.post_period_ratio,
        pull_forward_dip=o.pull_forward_dip,
    )


class RedemptionDemographicsResult(Base):
    __tablename__ = "redemption_demographics_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), index=True)
    redemption_count: Mapped[int] = mapped_column()
    under_25_count: Mapped[int] = mapped_column()
    under_25_share: Mapped[float] = mapped_column()
    customer_base_under_25_share: Mapped[float] = mapped_column()
    over_indexed_under_25: Mapped[bool] = mapped_column()


def redemption_demographics_to_orm(r: RedemptionDemographics) -> RedemptionDemographicsResult:
    return RedemptionDemographicsResult(
        promotion_id=r.promotion_id,
        redemption_count=r.redemption_count,
        under_25_count=r.under_25_count,
        under_25_share=r.under_25_share,
        customer_base_under_25_share=r.customer_base_under_25_share,
        over_indexed_under_25=r.over_indexed_under_25,
    )


def redemption_demographics_from_orm(o: RedemptionDemographicsResult) -> RedemptionDemographics:
    return RedemptionDemographics(
        promotion_id=o.promotion_id,
        redemption_count=o.redemption_count,
        under_25_count=o.under_25_count,
        under_25_share=o.under_25_share,
        customer_base_under_25_share=o.customer_base_under_25_share,
        over_indexed_under_25=o.over_indexed_under_25,
    )

class StockoutTraceResult(Base):
    __tablename__ = "stockout_trace_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.promotion_id"), index=True)
    any_stockout: Mapped[bool] = mapped_column()
    total_missed_units_estimate: Mapped[float] = mapped_column()

    sku_traces: Mapped[list[SkuInventoryTraceResult]] = relationship(
        back_populates="stockout_trace", cascade="all, delete-orphan"
    )


class SkuInventoryTraceResult(Base):
    __tablename__ = "sku_inventory_trace_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    stockout_trace_id: Mapped[int] = mapped_column(
        ForeignKey("stockout_trace_results.id"), index=True
    )
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.sku_id"), index=True)
    opening_stock: Mapped[int] = mapped_column()
    units_sold: Mapped[int] = mapped_column()
    closing_stock: Mapped[int] = mapped_column()
    stockout: Mapped[bool] = mapped_column()
    stockout_date: Mapped[date] = mapped_column()
    next_restock_date: Mapped[date] = mapped_column()
    missed_units_estimate: Mapped[float] = mapped_column()

    stockout_trace: Mapped[StockoutTraceResult] = relationship(back_populates="sku_traces")


def sku_inventory_trace_to_orm(s: SkuInventoryTrace) -> SkuInventoryTraceResult:
    return SkuInventoryTraceResult(
        sku_id=s.sku_id,
        opening_stock=s.opening_stock,
        units_sold=s.units_sold,
        closing_stock=s.closing_stock,
        stockout=s.stockout,
        stockout_date=s.stockout_date,
        next_restock_date=s.next_restock_date,
        missed_units_estimate=s.missed_units_estimate,
    )


def sku_inventory_trace_from_orm(o: SkuInventoryTraceResult) -> SkuInventoryTrace:
    return SkuInventoryTrace(
        sku_id=o.sku_id,
        opening_stock=o.opening_stock,
        units_sold=o.units_sold,
        closing_stock=o.closing_stock,
        stockout=o.stockout,
        stockout_date=o.stockout_date,
        next_restock_date=o.next_restock_date,
        missed_units_estimate=o.missed_units_estimate,
    )


def stockout_trace_to_orm(t: StockoutTrace) -> StockoutTraceResult:
    return StockoutTraceResult(
        promotion_id=t.promotion_id,
        any_stockout=t.any_stockout,
        total_missed_units_estimate=t.total_missed_units_estimate,
        sku_traces=[sku_inventory_trace_to_orm(s) for s in t.sku_traces],
    )


def stockout_trace_from_orm(o: StockoutTraceResult) -> StockoutTrace:
    return StockoutTrace(
        promotion_id=o.promotion_id,
        any_stockout=o.any_stockout,
        total_missed_units_estimate=o.total_missed_units_estimate,
        sku_traces=[sku_inventory_trace_from_orm(s) for s in o.sku_traces],
    )