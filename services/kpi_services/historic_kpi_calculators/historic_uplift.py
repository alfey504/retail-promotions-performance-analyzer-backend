"""
Historic (all-promotions) uplift report. Rewritten from the given version,
which had several real bugs -- see the conversation for the full list
(undefined variables causing a guaranteed NameError on the common path, dead
code computed then discarded, a duplicated/wrong zero-guard condition,
COUNT(*) instead of SUM(quantity), a hardcoded 30-day baseline window instead
of one matching each promotion's own duration, and zip()-based pairing that
silently misaligns the moment a promotion is missing from one side).

Architecture instead: fetch every promotion once, then call the existing,
already-validated get_incremental_sales_uplift() per promotion id. This reuses
the equal-length-baseline-window logic, the Decimal/float fix, and the
None-on-zero-baseline guard already built and tested in uplift_kpi.py, rather
than re-deriving (and re-risking) all of that in a second, parallel
implementation.
"""
from pydantic import BaseModel, ConfigDict

from utils import fetch_all_promotions
from uplift_kpi import Uplift, get_incremental_sales_uplift


class HistoricUplift(BaseModel):
    # Uplift (uplift_kpi.py) is a plain class, not a Pydantic BaseModel --
    # without this, Pydantic v2 can't build a schema for that field type and
    # raises at import time, not just at construction time.
    model_config = ConfigDict(arbitrary_types_allowed=True)

    promotion_id: int
    promotion_name: str
    promotion_type: str
    uplift: Uplift


def historic_uplift() -> list[HistoricUplift]:
    promotions = fetch_all_promotions()
    return [
        HistoricUplift(
            promotion_id=promotion_id,
            promotion_name=promotion_name,
            promotion_type=promotion_type,
            uplift=get_incremental_sales_uplift(promotion_id),
        )
        for promotion_id, promotion_name, promotion_type in promotions
    ]