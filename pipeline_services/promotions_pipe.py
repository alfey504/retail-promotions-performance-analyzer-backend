from api_services.promotions_api import get_promotions
from db_services.models import Promotion, PromotionSku, PromotionBundle
from db_services.promotions_db import add_promotions


def pipe_promotions():
    try:
        promotions = get_promotions()
        promotions_db = list[Promotion]()
        for promotion in promotions:
            promotion_db = Promotion(
                promotion_id = promotion.promotion_id,
                promotion_name = promotion.promotion_name,
                promotion_type = promotion.promotion_type,
                discount_percent = promotion.discount_percent,
                start_date = promotion.start_date,
                end_date =  promotion.end_date,
            )
            
            for sku_id in promotion.target_sku_ids:
                promotion_db.sku_links.append(
                    PromotionSku(sku_id=sku_id)
                )
            
            for bundle_id in promotion.target_bundle_ids:
                promotion_db.bundle_links.append(
                     PromotionBundle(bundle_id=bundle_id)
                )

            promotions_db.append(promotion_db)
        add_promotions(promotions_db)
    except Exception as e:
            raise e