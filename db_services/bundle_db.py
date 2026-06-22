from db_services.session import SessionLocal
from db_services.models import Bundle, BundleSku

def add_bundles(bundles: list[Bundle]):
    session = SessionLocal()

    try:
        session.add_all(bundles)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

def add_bundle(bundle: Bundle, sku_ids: list[int]):
    session = SessionLocal()

    try:
        session.add(bundle)
        session.commit()

        for sku_id in sku_ids:
            bundle.sku_links.append(
                BundleSku(sku_id=sku_id)
            )

        db.add(db_bundle)
        created_bundles.append(db_bundle)

    except Exception as e:
        raise e
    finally:
        session.close()
