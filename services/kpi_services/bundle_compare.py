"""
bundle_channel_comparator.py
─────────────────────────────────────────────────────────────────────────────
KPI: Bundle vs. Standalone Channel Comparator

Compares, for each bundle targeted by a promotion, the revenue and unit
volume earned through the bundle channel against what those exact same
component SKUs earned when sold individually (standalone) over the same
promotion window.

Answers the agent question:
  "Is bundling itself — not the discount — driving outperformance?"

Public entry point:
    bundle_vs_standalone_channel_comparator(session, promotion_id) -> dict
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from services.db_services.models import (
    Sale, SalePromotion, SkuSale, BundleSale,
    Promotion, Bundle, BundleSku, PromotionBundle, Sku,
)

from services.db_services.session import SessionLocal


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Database fetchers
# Raw ORM queries. Each function does exactly one thing: hit the DB and return rows.
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_promotion(session: Session, promotion_id: int) -> Promotion:
    """Load a Promotion row by PK. Raises ValueError if not found."""
    promo = session.get(Promotion, promotion_id)
    if promo is None:
        raise ValueError(f"Promotion {promotion_id} not found in database.")
    return promo


def _fetch_target_bundle_ids(session: Session, promotion_id: int) -> set[int]:
    """Return the set of bundle_ids targeted by this promotion (via PromotionBundle)."""
    links = (
        session.query(PromotionBundle)
        .filter(PromotionBundle.promotion_id == promotion_id)
        .all()
    )
    return {pb.bundle_id for pb in links}


def _fetch_promo_sales(
    session: Session, promotion_id: int, start: date, end: date
) -> list[Sale]:
    """
    Return Sale rows that fall within [start, end] AND reference this
    promotion via the SalePromotion junction table.
    """
    return (
        session.query(Sale)
        .join(SalePromotion, SalePromotion.sales_id == Sale.sales_id)
        .filter(
            SalePromotion.promotion_id == promotion_id,
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .all()
    )


def _fetch_bundle_sale_rows(
    session: Session, sale_ids: set[int], bundle_ids: set[int]
) -> list[BundleSale]:
    """BundleSale line items for the given sale IDs and bundle IDs."""
    return (
        session.query(BundleSale)
        .filter(
            BundleSale.sales_id.in_(sale_ids),
            BundleSale.bundle_id.in_(bundle_ids),
        )
        .all()
    )


def _fetch_component_skus(session: Session, bundle_id: int) -> list[BundleSku]:
    """BundleSku junction rows that define which SKUs make up a bundle."""
    return (
        session.query(BundleSku)
        .filter(BundleSku.bundle_id == bundle_id)
        .all()
    )


def _fetch_standalone_sku_rows(
    session: Session, sale_ids: set[int], sku_ids: set[int]
) -> list[SkuSale]:
    """
    SkuSale line items for the given sale IDs and SKU IDs.
    Caller is responsible for filtering out bundle-linked sales.
    """
    return (
        session.query(SkuSale)
        .filter(
            SkuSale.sales_id.in_(sale_ids),
            SkuSale.sku_id.in_(sku_ids),
        )
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Aggregators
# Take raw rows and produce counts / revenue figures.
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_bundle_units(bundle_sale_rows: list[BundleSale]) -> dict[int, int]:
    """Return {bundle_id: total_units_sold} from a list of BundleSale rows."""
    totals: dict[int, int] = defaultdict(int)
    for bs in bundle_sale_rows:
        totals[bs.bundle_id] += bs.quantity
    return totals


def _build_component_sku_info(
    session: Session, bundle_sku_links: list[BundleSku]
) -> tuple[list[dict], float]:
    """
    Resolve each BundleSku link into a component dict and sum list prices.

    Returns
    -------
    component_skus    : list of {sku_id, sku_name, list_price}
    sum_list_price    : float — sum of all component SKU list prices
    """
    component_skus = []
    sum_list_price = 0.0
    for link in bundle_sku_links:
        sku: Sku | None = session.get(Sku, link.sku_id)
        if sku:
            list_price = float(sku.price)
            sum_list_price += list_price
            component_skus.append({
                "sku_id":     sku.sku_id,
                "sku_name":   sku.sku_name,
                "list_price": list_price,
            })
    return component_skus, sum_list_price


def _aggregate_standalone_channel(
    standalone_sku_rows: list[SkuSale],
    sales_containing_bundle: set[int],
    sku_price_map: dict[int, tuple[str, float]],
) -> tuple[int, float, list[dict]]:
    """
    Aggregate standalone SKU sales, excluding transactions where the
    same bundle was also purchased (to avoid double-counting).

    Returns
    -------
    total_units    : int
    total_revenue  : float
    sku_breakdown  : list of {sku_id, sku_name, units, revenue}
    """
    by_sku: dict[int, int] = defaultdict(int)
    for ss in standalone_sku_rows:
        if ss.sales_id not in sales_containing_bundle:
            by_sku[ss.sku_id] += ss.quantity

    breakdown = []
    total_units   = 0
    total_revenue = 0.0
    for sku_id, units in by_sku.items():
        sku_name, list_price = sku_price_map.get(sku_id, ("Unknown", 0.0))
        rev = round(units * list_price, 2)
        total_units   += units
        total_revenue += rev
        breakdown.append({
            "sku_id":   sku_id,
            "sku_name": sku_name,
            "units":    units,
            "revenue":  rev,
        })
    return total_units, round(total_revenue, 2), breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Verdict builders
# Pure logic — no DB access, no aggregation. Just derive labels from numbers.
# ─────────────────────────────────────────────────────────────────────────────

def _compute_ratios(
    b_units: int, b_revenue: float,
    s_units: int, s_revenue: float,
) -> tuple[float | None, float | None, bool]:
    """
    Compute revenue_ratio, unit_ratio, and bundle_outperforms flag.

    Returns (revenue_ratio, unit_ratio, bundle_outperforms)
    """
    revenue_ratio = round(b_revenue / s_revenue, 2) if s_revenue > 0 else None
    unit_ratio    = round(b_units  / s_units,   2) if s_units  > 0 else None
    bundle_outperforms = revenue_ratio is not None and revenue_ratio > 1.0
    return revenue_ratio, unit_ratio, bundle_outperforms


def _channel_verdict(
    b_units: int, b_revenue: float,
    s_units: int, s_revenue: float,
    revenue_ratio: float | None,
    unit_ratio: float | None,
    bundle_outperforms: bool,
) -> str:
    """Human-readable verdict describing which channel won and by how much."""
    if b_units == 0 and s_units == 0:
        return "No sales recorded in either channel during this promotion window."
    if b_units == 0:
        return (
            f"Bundle had zero sales; component SKUs sold "
            f"{s_units} units standalone (${s_revenue:.2f})."
        )
    if s_units == 0:
        return (
            f"All demand flowed through the bundle "
            f"({b_units} units, ${b_revenue:.2f}); zero standalone sales of component SKUs."
        )
    if bundle_outperforms:
        return (
            f"Bundle channel outperforms standalone {revenue_ratio}× by revenue "
            f"(${b_revenue:.2f} vs ${s_revenue:.2f}) and {unit_ratio}× by units "
            f"({b_units} vs {s_units})."
        )
    return (
        f"Standalone channel outperforms bundle by revenue "
        f"(${s_revenue:.2f} vs ${b_revenue:.2f}). "
        f"Bundle revenue ratio: {revenue_ratio}×."
    )


def _driver_verdict(
    revenue_ratio: float | None,
    bundle_discount_pct: float,
) -> str:
    """
    Classify what is driving bundle outperformance.

    Logic (schema guarantees bundle discount is 12–22% below list):
      revenue_ratio ≥ 1.5 AND discount ≤ 22%  → bundle mechanic itself is converting
      revenue_ratio ≥ 1.0 AND discount > 15%  → discount is likely a significant factor
      revenue_ratio < 1.0 AND discount > 0%   → discount exists but bundling isn't converting
      otherwise                                → inconclusive

    Returns one of: "bundle-driven" | "mixed" | "discount-driven" | "inconclusive"
    """
    if revenue_ratio is None:
        return "inconclusive"
    if revenue_ratio >= 1.5 and bundle_discount_pct <= 22:
        return "bundle-driven"
    if revenue_ratio >= 1.0 and bundle_discount_pct > 15:
        return "mixed"
    if revenue_ratio < 1.0 and bundle_discount_pct > 0:
        return "discount-driven"
    return "inconclusive"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Result builders
# Assemble the final dicts that get returned to the agent.
# ─────────────────────────────────────────────────────────────────────────────

def _build_bundle_result(
    bundle: Bundle,
    component_skus: list[dict],
    sum_list_price: float,
    bundle_discount_pct: float,
    b_units: int,
    b_revenue: float,
    s_units: int,
    s_revenue: float,
    standalone_breakdown: list[dict],
) -> dict:
    """Assemble the full result dict for a single bundle."""
    revenue_ratio, unit_ratio, bundle_outperforms = _compute_ratios(
        b_units, b_revenue, s_units, s_revenue
    )
    return {
        "bundle_id":                   bundle.bundle_id,
        "bundle_name":                 bundle.bundle_name,
        "bundle_price":                float(bundle.bundle_price),
        "component_skus":              component_skus,
        "sum_component_list_price":    round(sum_list_price, 2),
        "bundle_discount_vs_list_pct": bundle_discount_pct,

        "bundle_channel": {
            "units_sold":    b_units,
            "gross_revenue": b_revenue,
        },
        "standalone_channel": {
            "units_sold":    s_units,
            "gross_revenue": s_revenue,
            "sku_breakdown": standalone_breakdown,
        },
        "comparator": {
            "revenue_ratio":      revenue_ratio,
            "unit_ratio":         unit_ratio,
            "bundle_outperforms": bundle_outperforms,
            "channel_verdict":    _channel_verdict(
                b_units, b_revenue, s_units, s_revenue,
                revenue_ratio, unit_ratio, bundle_outperforms,
            ),
            "driver_verdict":     _driver_verdict(revenue_ratio, bundle_discount_pct),
        },
    }


def _build_agent_summary(bundle_results: list[dict]) -> dict:
    """
    Roll up all bundle results into a top-level agent summary with
    flags and an overall verdict.
    """
    bundle_driven = [b for b in bundle_results if b["comparator"]["driver_verdict"] == "bundle-driven"]
    mixed         = [b for b in bundle_results if b["comparator"]["driver_verdict"] == "mixed"]
    underperform  = [b for b in bundle_results if not b["comparator"]["bundle_outperforms"]]
    flags         = []

    if bundle_driven:
        flags.append(
            f"{len(bundle_driven)} bundle(s) show genuine bundle-mechanic outperformance "
            f"beyond discount: {[b['bundle_name'] for b in bundle_driven]}. "
            f"Recommend rerunning these bundles without deeper discounts."
        )
    if mixed:
        flags.append(
            f"{len(mixed)} bundle(s) show mixed signals — discount may be inflating bundle appeal: "
            f"{[b['bundle_name'] for b in mixed]}. "
            f"Test at a shallower discount to isolate the mechanic effect."
        )
    if underperform:
        flags.append(
            f"{len(underperform)} bundle(s) underperform their standalone equivalents: "
            f"{[b['bundle_name'] for b in underperform]}. "
            f"Review component curation or pricing."
        )

    top = max(bundle_results, key=lambda b: b["bundle_channel"]["gross_revenue"], default=None)
    if top == None:
        raise Exception("failed to get maximum from bundle results , (max function returned None)")
    overall = (
        "No bundle sales data available." if not bundle_results
        else (
            f"Top bundle: '{top['bundle_name']}' — "
            f"${top['bundle_channel']['gross_revenue']:.2f} bundle revenue "
            f"({top['comparator']['revenue_ratio']}× standalone). "
            f"Driver: {top['comparator']['driver_verdict']}."
        )
    )

    return {
        "overall_verdict":       overall,
        "flags":                 flags,
        "bundle_driven_count":   len(bundle_driven),
        "mixed_count":           len(mixed),
        "underperforming_count": len(underperform),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def bundle_vs_standalone_channel_comparator(
    session: Session,
    promotion_id: int,
) -> dict[str, Any]:
    """
    KPI: Bundle vs. Standalone Channel Comparator

    For every bundle targeted by this promotion, compares:
      - Revenue & units sold through the BUNDLE channel
      - Revenue & units sold through the STANDALONE channel (same component SKUs)
    over the promotion's active date window, then derives a driver verdict.

    Parameters
    ----------
    session      : active SQLAlchemy Session
    promotion_id : int

    Returns
    -------
    {
        promotion_id   : int
        promotion_name : str
        window         : str       "YYYY-MM-DD → YYYY-MM-DD"
        bundles        : list[BundleResult]
        agent_summary  : dict
    }
    """

    # ── Fetch promotion & resolve window ─────────────────────────────────────
    promo              = _fetch_promotion(session, promotion_id)
    start, end         = promo.start_date, promo.end_date
    target_bundle_ids  = _fetch_target_bundle_ids(session, promotion_id)

    if not target_bundle_ids:
        return {
            "promotion_id":   promotion_id,
            "promotion_name": promo.promotion_name,
            "window":         f"{start} → {end}",
            "bundles":        [],
            "agent_summary":  {"overall_verdict": "No bundles targeted by this promotion.", "flags": []},
        }

    # ── Fetch sales & bundle line items ──────────────────────────────────────
    promo_sales      = _fetch_promo_sales(session, promotion_id, start, end)
    promo_sale_ids   = {s.sales_id for s in promo_sales}
    bundle_sale_rows = _fetch_bundle_sale_rows(session, promo_sale_ids, target_bundle_ids)
    bundle_units_map = _aggregate_bundle_units(bundle_sale_rows)

    # ── Build per-bundle results ──────────────────────────────────────────────
    bundle_results = []

    for bundle_id in target_bundle_ids:
        bundle = session.get(Bundle, bundle_id)
        if bundle is None:
            continue

        # Component SKUs
        bundle_sku_links           = _fetch_component_skus(session, bundle_id)
        component_skus, sum_list_p = _build_component_sku_info(session, bundle_sku_links)
        component_sku_ids          = {c["sku_id"] for c in component_skus}
        bundle_price               = float(bundle.bundle_price)
        bundle_discount_pct        = (
            round(((sum_list_p - bundle_price) / sum_list_p) * 100, 2)
            if sum_list_p > 0 else 0.0
        )

        # Bundle channel
        b_units   = bundle_units_map.get(bundle_id, 0)
        b_revenue = round(b_units * bundle_price, 2)

        # Standalone channel
        sales_with_this_bundle = {bs.sales_id for bs in bundle_sale_rows if bs.bundle_id == bundle_id}
        standalone_rows        = _fetch_standalone_sku_rows(session, promo_sale_ids, component_sku_ids)
        sku_price_map          = {c["sku_id"]: (c["sku_name"], c["list_price"]) for c in component_skus}
        s_units, s_revenue, standalone_breakdown = _aggregate_standalone_channel(
            standalone_rows, sales_with_this_bundle, sku_price_map
        )

        bundle_results.append(
            _build_bundle_result(
                bundle, component_skus, sum_list_p, bundle_discount_pct,
                b_units, b_revenue, s_units, s_revenue, standalone_breakdown,
            )
        )

    return {
        "promotion_id":   promotion_id,
        "promotion_name": promo.promotion_name,
        "window":         f"{start} → {end}",
        "bundles":        bundle_results,
        "agent_summary":  _build_agent_summary(bundle_results),
    }

def get_bundle_vs_standalone_channel_comparator(promotion_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try: 
        result = bundle_vs_standalone_channel_comparator(session, promotion_id=promotion_id)
        return result
    except Exception as e:
        print(f"Error: {e}")
        raise e
    finally:
        session.close()