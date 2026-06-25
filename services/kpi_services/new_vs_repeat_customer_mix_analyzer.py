"""
New vs. Repeat Customer Mix Analyzer
======================================
Compares the set of customer_ids buying during a promotion window against
a baseline window of equal length immediately preceding it.

A high customer overlap  → promo mostly discounted sales to buyers who'd
                           have purchased anyway (low incremental value).
A low customer overlap   → promo is genuinely acquiring new / lapsed buyers
                           (high incremental value).

Public API
----------
    check_customer_mix(session, promotion_id)                    -> dict
    find_customer_mix_kpis(session, promotion_id, *, verbose)    -> dict
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from services.db_services.models import Promotion, Sale, SalePromotion
from services.db_services.session import SessionLocal


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class CustomerSegments:
    """
    Holds the three mutually-exclusive customer populations derived from
    comparing the promo window against the baseline window.
    """

    promo_customer_ids:     set[int]   # bought during the promo window
    baseline_customer_ids:  set[int]   # bought during the baseline window

    @property
    def repeat_customer_ids(self) -> set[int]:
        """Customers who appear in BOTH windows (would likely have bought anyway)."""
        return self.promo_customer_ids & self.baseline_customer_ids

    @property
    def new_customer_ids(self) -> set[int]:
        """Customers who bought during the promo but NOT in the baseline window."""
        return self.promo_customer_ids - self.baseline_customer_ids

    @property
    def lapsed_customer_ids(self) -> set[int]:
        """Customers who bought in the baseline window but NOT during the promo."""
        return self.baseline_customer_ids - self.promo_customer_ids


# =============================================================================
# Private database helpers
# =============================================================================

def _fetch_promotion(session: Session, promotion_id: int) -> Promotion:
    """
    Load a Promotion row by primary key.

    Raises
    ------
    ValueError
        If no promotion with *promotion_id* exists.
    """
    promo = session.get(Promotion, promotion_id)
    if promo is None:
        raise ValueError(f"Promotion with id={promotion_id} not found.")
    return promo


def _fetch_promo_customer_ids(
    session:      Session,
    promotion_id: int,
    start_date:   date,
    end_date:     date,
) -> set[int]:
    """
    Return the set of customer_ids who made a purchase that referenced
    *promotion_id* within [start_date, end_date].

    Joins Sale → SalePromotion so only sales that explicitly claimed this
    promotion are included — not every sale that happened to fall inside
    the date window.
    """
    rows = session.execute(
        select(Sale.customer_id)
        .join(SalePromotion, SalePromotion.sales_id == Sale.sales_id)
        .where(
            and_(
                SalePromotion.promotion_id == promotion_id,
                Sale.sale_date >= start_date,
                Sale.sale_date <= end_date,
            )
        )
        .distinct()
    ).scalars().all()

    return set(rows)


def _fetch_baseline_customer_ids(
    session:    Session,
    start_date: date,
    end_date:   date,
) -> set[int]:
    """
    Return the set of customer_ids who made ANY purchase within
    [start_date, end_date] — the pre-promo baseline window.

    No promotion filter is applied here; we want to capture organic
    buying behaviour before the promotion ran.
    """
    rows = session.execute(
        select(Sale.customer_id)
        .where(
            and_(
                Sale.sale_date >= start_date,
                Sale.sale_date <= end_date,
            )
        )
        .distinct()
    ).scalars().all()

    return set(rows)


# =============================================================================
# Private window calculation
# =============================================================================

def _derive_baseline_window(
    promo_start: date,
    promo_end:   date,
) -> tuple[date, date]:
    """
    Derive a baseline window of the same length as the promo window,
    ending the day before the promotion started.

    Example
    -------
    Promo  : 2024-07-10 → 2024-07-20  (11 days)
    Baseline: 2024-06-29 → 2024-07-09  (11 days)
    """
    promo_length   = (promo_end - promo_start).days + 1
    baseline_end   = promo_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=promo_length - 1)
    return baseline_start, baseline_end


# =============================================================================
# Private KPI aggregation
# =============================================================================

def _aggregate_kpis(segments: CustomerSegments) -> dict[str, Any]:
    """
    Compute all planning KPIs from the three customer segments.

    KPIs
    ----
    total_promo_customers       : unique buyers during the promo window
    total_baseline_customers    : unique buyers during the baseline window
    repeat_customers            : in both windows (incremental risk)
    new_customers               : promo window only (incremental gain)
    lapsed_customers            : baseline only (did not return during promo)
    overlap_rate_pct            : repeat / promo  — high = low incrementality
    new_customer_rate_pct       : new   / promo  — high = strong acquisition
    lapsed_rate_pct             : lapsed / baseline — % of baseline buyers lost
    """
    n_promo    = len(segments.promo_customer_ids)
    n_baseline = len(segments.baseline_customer_ids)
    n_repeat   = len(segments.repeat_customer_ids)
    n_new      = len(segments.new_customer_ids)
    n_lapsed   = len(segments.lapsed_customer_ids)

    def pct(numerator: int, denominator: int) -> float:
        return round(numerator / denominator * 100, 2) if denominator else 0.0

    return {
        "total_promo_customers":    n_promo,
        "total_baseline_customers": n_baseline,
        "repeat_customers":         n_repeat,
        "new_customers":            n_new,
        "lapsed_customers":         n_lapsed,
        "overlap_rate_pct":         pct(n_repeat, n_promo),
        "new_customer_rate_pct":    pct(n_new,    n_promo),
        "lapsed_rate_pct":          pct(n_lapsed, n_baseline),
    }


def _derive_incrementality_verdict(overlap_rate_pct: float) -> str:
    """
    Translate overlap rate into a human-readable incrementality signal.

    Thresholds
    ----------
    < 30 %   → Strong acquisition  (mostly new buyers)
    30–60 %  → Mixed               (blend of new and repeat)
    > 60 %   → Low incrementality  (mostly discounting existing buyers)
    """
    if overlap_rate_pct < 30:
        return "STRONG_ACQUISITION"
    if overlap_rate_pct <= 60:
        return "MIXED"
    return "LOW_INCREMENTALITY"


# =============================================================================
# Private report printer
# =============================================================================

def _print_report(kpis: dict[str, Any]) -> None:
    """Pretty-print the full KPI report to stdout."""
    divider = "─" * 60

    verdict_labels = {
        "STRONG_ACQUISITION": "✅  STRONG ACQUISITION — promo is reaching new buyers",
        "MIXED":              "⚠️   MIXED — blend of new and repeat buyers",
        "LOW_INCREMENTALITY": "❌  LOW INCREMENTALITY — mostly discounting existing buyers",
    }

    print(divider)
    print("  NEW VS. REPEAT CUSTOMER MIX REPORT")
    print(divider)
    print(f"  Promotion     : [{kpis['promotion_id']}] {kpis['promotion_name']}")
    print(f"  Promo window  : {kpis['promo_start']}  →  {kpis['promo_end']}")
    print(f"  Base window   : {kpis['baseline_start']}  →  {kpis['baseline_end']}")
    print(divider)
    print("  CUSTOMER COUNTS")
    print(f"    Promo window buyers   : {kpis['total_promo_customers']}")
    print(f"    Baseline window buyers: {kpis['total_baseline_customers']}")
    print(f"    Repeat  (both windows): {kpis['repeat_customers']}")
    print(f"    New     (promo only)  : {kpis['new_customers']}")
    print(f"    Lapsed  (base only)   : {kpis['lapsed_customers']}")
    print(divider)
    print("  KPIs")
    print(f"    Overlap rate          : {kpis['overlap_rate_pct']} %")
    print(f"    New customer rate     : {kpis['new_customer_rate_pct']} %")
    print(f"    Lapsed rate           : {kpis['lapsed_rate_pct']} %")
    print(divider)
    print(f"  VERDICT")
    print(f"    {verdict_labels[kpis['incrementality_verdict']]}")
    print(divider)


# =============================================================================
# Public API
# =============================================================================

def check_customer_mix(
    session:      Session,
    promotion_id: int,
) -> dict[str, Any]:
    """
    New vs. Repeat Customer Mix Analyzer — core comparison.

    Compares the customer_ids who bought during the promotion window against
    those who bought in an equal-length baseline window immediately before it.

    Parameters
    ----------
    session      : active SQLAlchemy database session
    promotion_id : PK of the promotion to analyze

    Returns
    -------
    dict with keys:
        promotion_id         : int
        promotion_name       : str
        promo_start          : date
        promo_end            : date
        baseline_start       : date
        baseline_end         : date
        promo_customer_ids   : list[int]
        baseline_customer_ids: list[int]
        repeat_customer_ids  : list[int]
        new_customer_ids     : list[int]
        lapsed_customer_ids  : list[int]

    Raises
    ------
    ValueError
        If *promotion_id* does not exist in the database.
    """
    promo = _fetch_promotion(session, promotion_id)

    baseline_start, baseline_end = _derive_baseline_window(
        promo.start_date, promo.end_date
    )

    promo_customers    = _fetch_promo_customer_ids(
        session, promotion_id, promo.start_date, promo.end_date
    )
    baseline_customers = _fetch_baseline_customer_ids(
        session, baseline_start, baseline_end
    )

    segments = CustomerSegments(
        promo_customer_ids    = promo_customers,
        baseline_customer_ids = baseline_customers,
    )

    return {
        "promotion_id":          promo.promotion_id,
        "promotion_name":        promo.promotion_name,
        "promo_start":           promo.start_date,
        "promo_end":             promo.end_date,
        "baseline_start":        baseline_start,
        "baseline_end":          baseline_end,
        "promo_customer_ids":    sorted(segments.promo_customer_ids),
        "baseline_customer_ids": sorted(segments.baseline_customer_ids),
        "repeat_customer_ids":   sorted(segments.repeat_customer_ids),
        "new_customer_ids":      sorted(segments.new_customer_ids),
        "lapsed_customer_ids":   sorted(segments.lapsed_customer_ids),
    }


def find_customer_mix_kpis(
    session:      Session,
    promotion_id: int,
    *,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    New vs. Repeat Customer Mix Analyzer — KPI aggregator.

    Wraps ``check_customer_mix`` and surfaces the planning-level metrics
    needed to judge whether a promotion is acquiring incremental customers
    or simply discounting sales to buyers who would have purchased anyway.

    Parameters
    ----------
    session      : active SQLAlchemy database session
    promotion_id : PK of the promotion to analyze
    verbose      : when True, prints a formatted report to stdout

    Returns
    -------
    dict with all keys from ``check_customer_mix`` plus:
        total_promo_customers       : int
        total_baseline_customers    : int
        repeat_customers            : int
        new_customers               : int
        lapsed_customers            : int
        overlap_rate_pct            : float  — high = low incrementality
        new_customer_rate_pct       : float  — high = strong acquisition
        lapsed_rate_pct             : float  — % of baseline buyers not retained
        incrementality_verdict      : str    — STRONG_ACQUISITION | MIXED | LOW_INCREMENTALITY
    """
    result = check_customer_mix(session, promotion_id)

    segments = CustomerSegments(
        promo_customer_ids    = set(result["promo_customer_ids"]),
        baseline_customer_ids = set(result["baseline_customer_ids"]),
    )

    agg = _aggregate_kpis(segments)

    kpis = {
        **result,
        **agg,
        "incrementality_verdict": _derive_incrementality_verdict(agg["overlap_rate_pct"]),
    }

    if verbose:
        _print_report(kpis)

    return kpis
def get_find_customer_mix_kpis(promotion_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        result = find_customer_mix_kpis(session, promotion_id)
        return result
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()