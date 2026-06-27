
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.db_services.customer_db import customer_by_id 
from services.db_services.product_db import get_product_by_id
from services.db_services.promotions_db import  get_promotion_by_id 
from services.db_services.sku_db import  sku_by_id


def _safe_lookup(lookup_fn, entity_label: str, entity_id: int):
    """Returns (result, error_message). error_message is None on success.
    See the module docstring for why this treats any exception as not-found."""
    try:
        return lookup_fn(entity_id), None
    except Exception:
        return None, f"No {entity_label} found with id {entity_id}."

class CustomerLookupInput(BaseModel):
    customer_id: int = Field(..., description="The unique id of the customer to look up.")


def _format_customer(customer) -> str:
    return (
        f"Customer {customer.customer_id}: a {customer.customer_age}-year-old "
        f"{customer.customer_gender}, ethnicity {customer.ethnicity}."
    )


@tool(
    "get_customer_by_id",
    args_schema=CustomerLookupInput,
    response_format="content_and_artifact",
)
def customer_lookup_tool(customer_id: int):
    """Looks up a single customer by id and returns their age, gender, and
    ethnicity. Use this for simple "who is this customer" questions -- not
    for demographic analysis across many customers, which the redemption
    demographics KPI tool already covers."""
    customer, error = _safe_lookup(customer_by_id, "customer", customer_id)
    if error:
        return error, None
    return _format_customer(customer), customer

class ProductLookupInput(BaseModel):
    product_id: int = Field(..., description="The unique id of the product to look up.")


def _format_product(product) -> str:
    description = f" {product.product_description}" if product.product_description else ""
    return (
        f"Product {product.product_id}: '{product.product_name}', a "
        f"{product.product_category} by {product.product_brand}.{description}"
    )


@tool(
    "get_product_by_id",
    args_schema=ProductLookupInput,
    response_format="content_and_artifact",
)
def product_lookup_tool(product_id: int):
    """Looks up a single product by id and returns its name, brand, category,
    and description. A product is the general item (e.g. "Mattifying Pressed
    Powder"); use the SKU lookup tool instead for a specific size/color
    variant with its own price and stock level."""
    product, error = _safe_lookup(get_product_by_id, "product", product_id)
    if error:
        return error, None
    return _format_product(product), product


class PromotionLookupInput(BaseModel):
    promotion_id: int = Field(..., description="The unique id of the promotion to look up.")


def _format_promotion(promotion) -> str:
    sku_ids = sorted(link.sku_id for link in promotion.sku_links)

    if promotion.discount_percent not in (None, 0):
        discount_clause = f", offering a {promotion.discount_percent}% discount"
    elif promotion.promotion_type == "BOGO":
        discount_clause = ""
    else:
        discount_clause = ", with a BOGO-style mechanic instead of a flat discount percentage"

    sku_clause = (
        f"targeting {len(sku_ids)} SKU(s): {sku_ids}" if sku_ids
        else "with no SKUs currently targeted"
    )

    return (
        f"Promotion {promotion.promotion_id}: '{promotion.promotion_name}', a "
        f"{promotion.promotion_type} promotion{discount_clause}, running "
        f"{promotion.start_date} to {promotion.end_date}, {sku_clause}."
    )


@tool(
    "get_promotion_by_id",
    args_schema=PromotionLookupInput,
    response_format="content_and_artifact",
)
def promotion_lookup_tool(promotion_id: int):
    """Looks up a single promotion by id and returns its name, type, discount
    mechanic, date range, and which SKUs it targets. Use this for "what is
    this promotion" questions -- for performance questions (did it work, did
    it cause a stockout, etc.) use the dedicated KPI tools instead."""
    promotion, error = _safe_lookup(get_promotion_by_id, "promotion", promotion_id)
    if error:
        return error, None
    return _format_promotion(promotion), promotion


class SkuLookupInput(BaseModel):
    sku_id: int = Field(..., description="The unique id of the SKU to look up.")


def _format_sku(sku) -> str:
    variant_bits = [b for b in (sku.size, sku.color) if b]
    variant = f" ({', '.join(variant_bits)})" if variant_bits else ""
    stock_note = f"{sku.in_stock} unit(s) in stock" if sku.in_stock > 0 else "out of stock"
    return (
        f"SKU {sku.sku_id}: '{sku.sku_name}'{variant}, priced at ${sku.price:,.2f}, {stock_note}."
    )


@tool(
    "get_sku_by_id",
    args_schema=SkuLookupInput,
    response_format="content_and_artifact",
)
def sku_lookup_tool(sku_id: int):
    """Looks up a single SKU by id and returns its name, size/color variant,
    price, and current stock level. A SKU is a specific purchasable variant
    of a product (e.g. a particular size and color); use the product lookup
    tool instead for the general item it belongs to."""
    sku, error = _safe_lookup(sku_by_id, "SKU", sku_id)
    if error:
        return error, None
    return _format_sku(sku), sku