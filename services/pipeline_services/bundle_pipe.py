from  services.api_services.bundle_api import get_bundles
from  services.db_services.models import Bundle, BundleSku
from  services.db_services.bundle_db import add_bundles


def pipe_bundle():
    try:
        bundels = get_bundles()
        bundles_db = list[Bundle]()
        for bundle in bundels:
            bundle_db = Bundle(
                bundle_id = bundle.bundle_id,
                bundle_name = bundle.bundle_name,
                bundle_description = bundle.bundle_description,
                bundle_price = bundle.bundle_price
            )
            
            for sku_id in bundle.sku_ids:
                bundle_db.sku_links.append(
                    BundleSku(sku_id=sku_id)
                )

            bundles_db.append(bundle_db)
        add_bundles(bundles_db)
    except Exception as e:
            raise e