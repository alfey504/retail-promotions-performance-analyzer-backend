"""
Promotion Scheduling Guardrail
================================
Checks a proposed promotion's SKU/bundle set against every currently
scheduled promotion for time-overlap collisions before the promotion
goes live.

Public API
----------
    check_promotion_conflicts(session, promotion_id)  ->  dict
    find_promotion_conflict_kpis(session, promotion_id, *, verbose)  ->  dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from services.db_services.models import Promotion, PromotionBundle, PromotionSku
from services.db_services.session import SessionLocal


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class ConflictDetail:
    """Describes a single scheduling conflict between two promotions."""

    conflicting_promotion_id:   int
    conflicting_promotion_name: str
    overlap_start:              date
    overlap_end:                date
    shared_sku_ids:             list[int] = field(default_factory=list)
    shared_bundle_ids:          list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflicting_promotion_id":   self.conflicting_promotion_id,
            "conflicting_promotion_name": self.conflicting_promotion_name,
            "overlap_start":              self.overlap_start,
            "overlap_end":                self.overlap_end,
            "shared_sku_ids":             self.shared_sku_ids,
            "shared_bundle_ids":          self.shared_bundle_ids,
        }


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


def _fetch_sku_ids(session: Session, promotion_id: int) -> list[int]:
    """Return all SKU IDs targeted by the given promotion."""
    return list(
        session.execute(
            select(PromotionSku.sku_id)
            .where(PromotionSku.promotion_id == promotion_id)
        ).scalars().all()
    )


def _fetch_bundle_ids(session: Session, promotion_id: int) -> list[int]:
    """Return all bundle IDs targeted by the given promotion."""
    return list(
        session.execute(
            select(PromotionBundle.bundle_id)
            .where(PromotionBundle.promotion_id == promotion_id)
        ).scalars().all()
    )


def _fetch_time_overlapping_promotions(
    session:      Session,
    promotion_id: int,
    start_date:   date,
    end_date:     date,
) -> list[Promotion]:
    """
    Return every promotion (excluding *promotion_id* itself) whose date
    window intersects [start_date, end_date].

    Two closed intervals A and B overlap when:
        A.start <= B.end  AND  B.start <= A.end
    """
    return list(
        session.execute(
            select(Promotion).where(
                and_(
                    Promotion.promotion_id != promotion_id,
                    Promotion.start_date   <= end_date,
                    Promotion.end_date     >= start_date,
                )
            )
        ).scalars().all()
    )


# =============================================================================
# Private conflict-detection logic
# =============================================================================

def _compute_conflict(
    candidate:       Promotion,
    promo_sku_ids:   list[int],
    promo_bundle_ids: list[int],
    session:         Session,
) -> ConflictDetail | None:
    """
    Compare *candidate* against the proposed promotion's SKU/bundle sets.

    Returns a ConflictDetail if they share at least one SKU or bundle,
    otherwise returns None.
    """
    other_sku_ids    = _fetch_sku_ids(session, candidate.promotion_id)
    other_bundle_ids = _fetch_bundle_ids(session, candidate.promotion_id)

    shared_skus    = sorted(set(promo_sku_ids)    & set(other_sku_ids))
    shared_bundles = sorted(set(promo_bundle_ids) & set(other_bundle_ids))

    if not shared_skus and not shared_bundles:
        return None

    return ConflictDetail(
        conflicting_promotion_id   = candidate.promotion_id,
        conflicting_promotion_name = candidate.promotion_name,
        overlap_start              = candidate.start_date,
        overlap_end                = candidate.end_date,
        shared_sku_ids             = shared_skus,
        shared_bundle_ids          = shared_bundles,
    )


def _build_conflicts(
    session:          Session,
    promotion_id:     int,
    promo_sku_ids:    list[int],
    promo_bundle_ids: list[int],
    start_date:       date,
    end_date:         date,
) -> list[ConflictDetail]:
    """
    Find all conflicts for the proposed promotion against every
    time-overlapping promotion in the database.
    """
    candidates = _fetch_time_overlapping_promotions(
        session, promotion_id, start_date, end_date
    )

    conflicts = []
    for candidate in candidates:
        conflict = _compute_conflict(
            candidate, promo_sku_ids, promo_bundle_ids, session
        )
        if conflict:
            conflicts.append(conflict)

    return conflicts


# =============================================================================
# Private KPI aggregation
# =============================================================================

def _aggregate_kpis(conflicts: list[ConflictDetail]) -> dict[str, Any]:
    """
    Derive planning KPIs from a list of ConflictDetail objects.

    KPIs
    ----
    total_conflicting_promotions    : number of promotions that clash
    total_shared_skus_across_all    : deduplicated SKU collision count
    total_shared_bundles_across_all : deduplicated bundle collision count
    max_overlap_days                : length of the longest single overlap window
    earliest_overlap_start          : start of the first conflict window
    latest_overlap_end              : end of the last conflict window
    """
    all_shared_skus    = set()
    all_shared_bundles = set()
    max_overlap_days   = 0
    earliest_start: date | None = None
    latest_end:     date | None = None

    for c in conflicts:
        all_shared_skus    |= set(c.shared_sku_ids)
        all_shared_bundles |= set(c.shared_bundle_ids)

        days = (c.overlap_end - c.overlap_start).days + 1
        if days > max_overlap_days:
            max_overlap_days = days

        if earliest_start is None or c.overlap_start < earliest_start:
            earliest_start = c.overlap_start
        if latest_end is None or c.overlap_end > latest_end:
            latest_end = c.overlap_end

    return {
        "total_conflicting_promotions":    len(conflicts),
        "total_shared_skus_across_all":    len(all_shared_skus),
        "total_shared_bundles_across_all": len(all_shared_bundles),
        "max_overlap_days":                max_overlap_days,
        "earliest_overlap_start":          earliest_start,
        "latest_overlap_end":              latest_end,
    }


# =============================================================================
# Private report printer
# =============================================================================

def _print_report(kpis: dict[str, Any]) -> None:
    """Pretty-print the full KPI report to stdout."""
    divider = "─" * 60

    print(divider)
    print("  PROMOTION SCHEDULING GUARDRAIL REPORT")
    print(divider)
    print(f"  Promotion : [{kpis['promotion_id']}] {kpis['promotion_name']}")
    print(f"  Period    : {kpis['start_date']}  →  {kpis['end_date']}")
    print(f"  SKUs      : {kpis['target_skus']    or '(none)'}")
    print(f"  Bundles   : {kpis['target_bundles'] or '(none)'}")
    print(divider)

    if kpis["is_safe_to_run"]:
        print("  ✅  SAFE TO SCHEDULE — no conflicts found.")
        print(divider)
        return

    print("  ❌  CONFLICTS DETECTED — do NOT schedule as-is.\n")
    print("  KPIs")
    print(f"    Conflicting promotions       : {kpis['total_conflicting_promotions']}")
    print(f"    Unique shared SKUs           : {kpis['total_shared_skus_across_all']}")
    print(f"    Unique shared bundles        : {kpis['total_shared_bundles_across_all']}")
    print(f"    Longest overlap (days)       : {kpis['max_overlap_days']}")
    print(f"    Earliest conflict start      : {kpis['earliest_overlap_start']}")
    print(f"    Latest conflict end          : {kpis['latest_overlap_end']}")
    print()
    print("  CONFLICT DETAIL")

    for i, c in enumerate(kpis["conflict_summary"], 1):
        print(f"    [{i}] Promotion {c['conflicting_promotion_id']}: "
              f"{c['conflicting_promotion_name']}")
        print(f"        Overlap  : {c['overlap_start']} → {c['overlap_end']}")
        print(f"        SKUs     : {c['shared_sku_ids']    or '—'}")
        print(f"        Bundles  : {c['shared_bundle_ids'] or '—'}")

    print(divider)


# =============================================================================
# Public API
# =============================================================================

def check_promotion_conflicts(
    session:      Session,
    promotion_id: int,
) -> dict[str, Any]:
    """
    Promotion Scheduling Guardrail — core conflict checker.

    Checks the proposed promotion's SKU/bundle set against every currently
    scheduled promotion for time-overlap collisions.

    Parameters
    ----------
    session      : active SQLAlchemy database session
    promotion_id : PK of the promotion to audit (may be a draft/not-yet-active row)

    Returns
    -------
    dict with keys:
        promotion_id    : int
        promotion_name  : str
        start_date      : date
        end_date        : date
        target_skus     : list[int]
        target_bundles  : list[int]
        conflicts       : list[dict]   — empty when no conflicts exist
        is_safe_to_run  : bool

    Raises
    ------
    ValueError
        If *promotion_id* does not exist in the database.
    """
    promo            = _fetch_promotion(session, promotion_id)
    promo_sku_ids    = _fetch_sku_ids(session, promotion_id)
    promo_bundle_ids = _fetch_bundle_ids(session, promotion_id)

    conflicts = _build_conflicts(
        session, promotion_id,
        promo_sku_ids, promo_bundle_ids,
        promo.start_date, promo.end_date,
    )

    return {
        "promotion_id":   promo.promotion_id,
        "promotion_name": promo.promotion_name,
        "start_date":     promo.start_date,
        "end_date":       promo.end_date,
        "target_skus":    promo_sku_ids,
        "target_bundles": promo_bundle_ids,
        "conflicts":      [c.to_dict() for c in conflicts],
        "is_safe_to_run": len(conflicts) == 0,
    }


def find_promotion_conflict_kpis(
    session:      Session,
    promotion_id: int,
    *,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Promotion Scheduling Guardrail — KPI aggregator.

    Wraps ``check_promotion_conflicts`` and surfaces the planning-level
    metrics an agent or reviewer needs to decide whether a promotion is
    safe to schedule.

    Parameters
    ----------
    session      : active SQLAlchemy database session
    promotion_id : PK of the promotion to audit
    verbose      : when True, prints a formatted report to stdout

    Returns
    -------
    dict with all keys from ``check_promotion_conflicts`` plus:
        total_conflicting_promotions    : int
        total_shared_skus_across_all    : int  (deduplicated)
        total_shared_bundles_across_all : int  (deduplicated)
        max_overlap_days                : int
        earliest_overlap_start          : date | None
        latest_overlap_end              : date | None
        conflict_summary                : list[dict]  — per-conflict breakdown
    """
    result    = check_promotion_conflicts(session, promotion_id)
    conflicts = [
        ConflictDetail(
            conflicting_promotion_id   = c["conflicting_promotion_id"],
            conflicting_promotion_name = c["conflicting_promotion_name"],
            overlap_start              = c["overlap_start"],
            overlap_end                = c["overlap_end"],
            shared_sku_ids             = c["shared_sku_ids"],
            shared_bundle_ids          = c["shared_bundle_ids"],
        )
        for c in result["conflicts"]
    ]

    kpis = {
        **result,
        **_aggregate_kpis(conflicts),
        "conflict_summary": result["conflicts"],
    }

    if verbose:
        _print_report(kpis)

    return kpis

def get_find_promotion_conflict(promotion_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        result = find_promotion_conflict_kpis(session, promotion_id)
        return result
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()