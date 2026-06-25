from services.rag_services.qdrant_services import search_query
from services.kpi_services.incremental_uplift_calculator import get_uplift_for_promotion
from services.kpi_services.discount_efficiency_ratio import get_discount_efficiency_ratio
from services.kpi_services.promotion_fatigue_tracker import get_promotion_fatigue_tracker


def main():
    uplifts = get_promotion_fatigue_tracker(60)
    for  k, v in uplifts.items():
        print(v.promo_revenue)
    return


if __name__ == "__main__":
    main()

