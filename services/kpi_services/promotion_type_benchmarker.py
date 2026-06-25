"""
Promotion-Type Benchmarker
============================
Aggregates incremental uplift and discount efficiency across all promotions
grouped by promotion_type (e.g. Percentage Off, BOGO, Flash Sale,
Bundle Discount, Seasonal Sale).

Answers "which mechanic works best on average" — a question none of the
per-promotion tools can answer since they only ever look at one promotion
at a time.

Metrics computed per promotion_type
-------------------------------------
    total_promotions          : number of promotions of this type
    total_promo_revenue       : sum of final_price across all promo-window sales
    total_baseline_revenue    : sum of final_price across matching baseline windows
    incremental_revenue       : promo_revenue - baseline_revenue
    avg_incremental_revenue   : incremental_revenue / total_promotions
    total_promo_customers     : unique buyers across all promo windows
    total_new_customers       : buyers who did not appear in any matching baseline
    new_customer_rate_pct     : new_customers / promo_customers
    avg_discount_pct          : mean discount_percent across promotions of this type
    discount_efficiency       : incremental_revenue / (revenue foregone to discount)
    best_promotion_id         : id of the single promotion with highest incremental revenue
    best_promotion_name       : name of that promotion

Public API
----------
    check_promotion_type_benchmarks(session)                    -> dict
    find_promotion_type_benchmark_kpis(session, *, verbose)     -> dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from services.db_services.models import Promotion, Sale, SalePromotion
from services.db_services.session import SessionLocal


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class PromotionMetrics:
    """
    Raw aggregated numbers for a single promotion, collected before
    grouping by promotion_type.
    """

    promotion_id:       int
    promotion_name:     str
    promotion_type:     str
    discount_percent:   float          # 0 when NULL in DB (e.g. BOGO)
    promo_revenue:      float
    baseline_revenue:   float
    promo_customer_ids: set[int]
    baseline_customer_ids: set[int]

    @property
    def incremental_revenue(self) -> float:
        return self.promo_revenue - self.baseline_revenue

    @property
    def new_customer_ids(self) -> set[int]:
        return self.promo_customer_ids - self.baseline_customer_ids


@dataclass
class TypeBenchmark:
    """
    Aggregated KPIs for one promotion_type, derived from a list of
    PromotionMetrics belonging to that type.
    """

    promotion_type:           str
    promotion_metrics:        list[PromotionMetrics] = field(default_factory=list)

    # ---- aggregated fields (populated by _aggregate_type_benchmark) ----
    total_promotions:         int   = 0
    total_promo_revenue:      float = 0.0
    total_baseline_revenue:   float = 0.0
    incremental_revenue:      float = 0.0
    avg_incremental_revenue:  float = 0.0
    total_promo_customers:    int   = 0
    total_new_customers:      int   = 0
    new_customer_rate_pct:    float = 0.0
    avg_discount_pct:         float = 0.0
    discount_efficiency:      float = 0.0
    best_promotion_id:        int | None   = None
    best_promotion_name:      str | None   = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_type":          self.promotion_type,
            "total_promotions":        self.total_promotions,
            "total_promo_revenue":     round(self.total_promo_revenue,    2),
            "total_baseline_revenue":  round(self.total_baseline_revenue, 2),
            "incremental_revenue":     round(self.incremental_revenue,    2),
            "avg_incremental_revenue": round(self.avg_incremental_revenue,2),
            "total_promo_customers":   self.total_promo_customers,
            "total_new_customers":     self.total_new_customers,
            "new_customer_rate_pct":   self.new_customer_rate_pct,
            "avg_discount_pct":        self.avg_discount_pct,
            "discount_efficiency":     self.discount_efficiency,
            "best_promotion_id":       self.best_promotion_id,
            "best_promotion_name":     self.best_promotion_name,
        }


# =============================================================================
# Private database helpers
# =============================================================================

def _fetch_all_promotions(session: Session) -> list[Promotion]:
    """Return every promotion row in the database, ordered by start_date."""
    return list(
        session.execute(
            select(Promotion).order_by(Promotion.start_date)
        ).scalars().all()
    )


def _fetch_window_revenue(
    session:      Session,
    promotion_id: int | None,
    start_date:   date,
    end_date:     date,
) -> float:
    """
    Sum final_price for all sales within [start_date, end_date].

    When *promotion_id* is provided the query joins through SalePromotion
    so only sales that explicitly claimed that promotion are counted.
    When *promotion_id* is None a plain date-range scan is used (baseline).
    """
    if promotion_id is not None:
        result = session.execute(
            select(func.coalesce(func.sum(Sale.final_price), 0))
            .join(SalePromotion, SalePromotion.sales_id == Sale.sales_id)
            .where(
                and_(
                    SalePromotion.promotion_id == promotion_id,
                    Sale.sale_date >= start_date,
                    Sale.sale_date <= end_date,
                )
            )
        ).scalar()
    else:
        result = session.execute(
            select(func.coalesce(func.sum(Sale.final_price), 0))
            .where(
                and_(
                    Sale.sale_date >= start_date,
                    Sale.sale_date <= end_date,
                )
            )
        ).scalar()

    return float(result or 0.0)


def _fetch_window_customer_ids(
    session:      Session,
    promotion_id: int | None,
    start_date:   date,
    end_date:     date,
) -> set[int]:
    """
    Return the set of distinct customer_ids who purchased within
    [start_date, end_date].

    When *promotion_id* is provided, only sales that claimed that
    promotion are included (promo window).
    When *promotion_id* is None, all sales in the window are included
    (baseline window).
    """
    if promotion_id is not None:
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
    else:
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
    Return a baseline window of the same length as the promo window,
    ending the day before the promotion started.

    Example
    -------
    Promo    : 2024-07-10 → 2024-07-20  (11 days)
    Baseline : 2024-06-29 → 2024-07-09  (11 days)
    """
    length         = (promo_end - promo_start).days + 1
    baseline_end   = promo_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=length - 1)
    return baseline_start, baseline_end


# =============================================================================
# Private per-promotion metric builder
# =============================================================================

def _build_promotion_metrics(
    session: Session,
    promo:   Promotion,
) -> PromotionMetrics:
    """
    Collect all raw numbers for a single promotion by querying its
    promo window and a matched baseline window of equal length.
    """
    baseline_start, baseline_end = _derive_baseline_window(
        promo.start_date, promo.end_date
    )

    promo_revenue    = _fetch_window_revenue(
        session, promo.promotion_id, promo.start_date, promo.end_date
    )
    baseline_revenue = _fetch_window_revenue(
        session, None, baseline_start, baseline_end
    )
    promo_customers  = _fetch_window_customer_ids(
        session, promo.promotion_id, promo.start_date, promo.end_date
    )
    baseline_customers = _fetch_window_customer_ids(
        session, None, baseline_start, baseline_end
    )

    return PromotionMetrics(
        promotion_id          = promo.promotion_id,
        promotion_name        = promo.promotion_name,
        promotion_type        = promo.promotion_type,
        discount_percent      = float(promo.discount_percent or 0),
        promo_revenue         = promo_revenue,
        baseline_revenue      = baseline_revenue,
        promo_customer_ids    = promo_customers,
        baseline_customer_ids = baseline_customers,
    )


# =============================================================================
# Private per-type aggregation
# =============================================================================

def _aggregate_type_benchmark(benchmark: TypeBenchmark) -> TypeBenchmark:
    """
    Populate all aggregated fields on a TypeBenchmark from its list of
    PromotionMetrics.  Mutates and returns the same object.
    """
    metrics = benchmark.promotion_metrics
    if not metrics:
        return benchmark

    n = len(metrics)

    # ---- revenue & incrementality ----------------------------------------
    total_promo_rev  = sum(m.promo_revenue      for m in metrics)
    total_base_rev   = sum(m.baseline_revenue   for m in metrics)
    incremental_rev  = total_promo_rev - total_base_rev

    # ---- customer acquisition --------------------------------------------
    all_promo_customers = set().union(*(m.promo_customer_ids for m in metrics))
    all_new_customers   = set().union(*(m.new_customer_ids   for m in metrics))
    n_promo_cust        = len(all_promo_customers)
    n_new_cust          = len(all_new_customers)

    # ---- discount efficiency  =  incremental_revenue / revenue_foregone --
    # revenue_foregone ≈ promo_revenue * (avg_discount_pct / 100)
    avg_discount = sum(m.discount_percent for m in metrics) / n
    revenue_foregone = total_promo_rev * (avg_discount / 100) if avg_discount else 0.0
    efficiency = (
        round(incremental_rev / revenue_foregone, 4)
        if revenue_foregone > 0
        else 0.0
    )

    # ---- best single promotion -------------------------------------------
    best = max(metrics, key=lambda m: m.incremental_revenue)

    def pct(num: int, den: int) -> float:
        return round(num / den * 100, 2) if den else 0.0

    benchmark.total_promotions        = n
    benchmark.total_promo_revenue     = total_promo_rev
    benchmark.total_baseline_revenue  = total_base_rev
    benchmark.incremental_revenue     = incremental_rev
    benchmark.avg_incremental_revenue = incremental_rev / n
    benchmark.total_promo_customers   = n_promo_cust
    benchmark.total_new_customers     = n_new_cust
    benchmark.new_customer_rate_pct   = pct(n_new_cust, n_promo_cust)
    benchmark.avg_discount_pct        = round(avg_discount, 2)
    benchmark.discount_efficiency     = efficiency
    benchmark.best_promotion_id       = best.promotion_id
    benchmark.best_promotion_name     = best.promotion_name

    return benchmark


# =============================================================================
# Private grouping logic
# =============================================================================

def _group_metrics_by_type(
    all_metrics: list[PromotionMetrics],
) -> dict[str, TypeBenchmark]:
    """
    Partition PromotionMetrics by promotion_type and return a dict keyed
    by promotion_type with an unsummarised TypeBenchmark for each group.
    """
    groups: dict[str, TypeBenchmark] = {}
    for m in all_metrics:
        if m.promotion_type not in groups:
            groups[m.promotion_type] = TypeBenchmark(promotion_type=m.promotion_type)
        groups[m.promotion_type].promotion_metrics.append(m)
    return groups


def _rank_types_by_incrementality(
    benchmarks: list[TypeBenchmark],
) -> list[TypeBenchmark]:
    """Return benchmarks sorted descending by incremental_revenue."""
    return sorted(benchmarks, key=lambda b: b.incremental_revenue, reverse=True)


# =============================================================================
# Private report printer
# =============================================================================

def _print_report(kpis: dict[str, Any]) -> None:
    """Pretty-print the full benchmark report to stdout."""
    divider = "─" * 65

    print(divider)
    print("  PROMOTION-TYPE BENCHMARKER REPORT")
    print(divider)
    print(f"  Total promotion types analysed : {kpis['total_promotion_types']}")
    print(f"  Total promotions analysed      : {kpis['total_promotions_analysed']}")
    print(f"  Best performing type           : {kpis['best_promotion_type']}")
    print(divider)

    for rank, b in enumerate(kpis["type_benchmarks"], 1):
        print(f"\n  [{rank}] {b['promotion_type']}")
        print(f"       Promotions            : {b['total_promotions']}")
        print(f"       Promo revenue         : {b['total_promo_revenue']:,.2f}")
        print(f"       Baseline revenue      : {b['total_baseline_revenue']:,.2f}")
        print(f"       Incremental revenue   : {b['incremental_revenue']:,.2f}")
        print(f"       Avg incremental / promo: {b['avg_incremental_revenue']:,.2f}")
        print(f"       Promo customers       : {b['total_promo_customers']}")
        print(f"       New customers         : {b['total_new_customers']}")
        print(f"       New customer rate     : {b['new_customer_rate_pct']} %")
        print(f"       Avg discount          : {b['avg_discount_pct']} %")
        print(f"       Discount efficiency   : {b['discount_efficiency']}")
        print(f"       Best promotion        : [{b['best_promotion_id']}] {b['best_promotion_name']}")

    print(f"\n{divider}")


# =============================================================================
# Public API
# =============================================================================

def check_promotion_type_benchmarks(session: Session) -> dict[str, Any]:
    """
    Promotion-Type Benchmarker — core aggregation.

    Fetches every promotion in the database, computes per-promotion metrics
    against a matched baseline window, then groups and aggregates those
    metrics by promotion_type.

    Parameters
    ----------
    session : active SQLAlchemy database session

    Returns
    -------
    dict with keys:
        total_promotion_types      : int
        total_promotions_analysed  : int
        best_promotion_type        : str  — type with highest incremental revenue
        type_benchmarks            : list[dict]  — one entry per promotion_type,
                                     sorted descending by incremental_revenue
    """
    all_promotions = _fetch_all_promotions(session)

    all_metrics = [
        _build_promotion_metrics(session, promo)
        for promo in all_promotions
    ]

    groups     = _group_metrics_by_type(all_metrics)
    benchmarks = [
        _aggregate_type_benchmark(b) for b in groups.values()
    ]
    ranked = _rank_types_by_incrementality(benchmarks)

    return {
        "total_promotion_types":     len(ranked),
        "total_promotions_analysed": len(all_metrics),
        "best_promotion_type":       ranked[0].promotion_type if ranked else None,
        "type_benchmarks":           [b.to_dict() for b in ranked],
    }


def find_promotion_type_benchmark_kpis(
    session: Session,
    *,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Promotion-Type Benchmarker — KPI surface.

    Wraps ``check_promotion_type_benchmarks`` and adds cross-type comparative
    KPIs that highlight the standout mechanic on each dimension.

    Parameters
    ----------
    session : active SQLAlchemy database session
    verbose : when True, prints a formatted report to stdout

    Returns
    -------
    dict with all keys from ``check_promotion_type_benchmarks`` plus:
        highest_new_customer_rate_type   : str  — best acquisition mechanic
        highest_discount_efficiency_type : str  — best revenue-per-discount type
        highest_avg_incremental_type     : str  — best avg lift per promo run
    """
    result = check_promotion_type_benchmarks(session)

    benchmarks = result["type_benchmarks"]

    def top_type(key: str) -> str | None:
        return max(benchmarks, key=lambda b: b[key])["promotion_type"] if benchmarks else None

    kpis = {
        **result,
        "highest_new_customer_rate_type":   top_type("new_customer_rate_pct"),
        "highest_discount_efficiency_type": top_type("discount_efficiency"),
        "highest_avg_incremental_type":     top_type("avg_incremental_revenue"),
    }

    if verbose:
        _print_report(kpis)

    return kpis
def get_find_promotion_type_benchmark_kpis(promotion_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        result = find_promotion_type_benchmark_kpis(session, promotion_id)
        return result
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()