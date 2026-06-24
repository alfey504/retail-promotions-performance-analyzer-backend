from pydantic import BaseModel, Field
from typing import List, Generic, TypeVar
from pydantic import BaseModel
from typing import Optional
from datetime import date

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    status: int
    message: str
    data: List[T]

class PagedAPIResponse(BaseModel, Generic[T]):
    status: int
    message: str

    page: int
    max_page: int

    data: List[T]

class Product(BaseModel):
    product_id: int
    product_name: str
    product_description: str
    product_brand: str
    product_category: str



class SKU(BaseModel):
    sku_id: int
    product_id: int
    sku_name: str
    size: str
    color: str

    last_fulfillment_date: Optional[date] = None
    next_fulfillment_date: Optional[date] = None

    in_stock: int
    price: float


class Customer(BaseModel):
    customer_id: int
    customer_age: int
    customer_gender: str
    ethnicity: str

class Fulfillment(BaseModel):
    fulfillment_id: int
    sku_id: int
    fulfillment_date: date
    quantity_received: int


class Bundle(BaseModel):
    bundle_id: int
    bundle_name: str
    bundle_description: str
    bundle_price: float

    sku_ids: List[int]

class Promotion(BaseModel):
    promotion_id: int

    promotion_name: str
    promotion_description: str

    promotion_type: str

    target_bundle_ids: Optional[List[int]]
    target_sku_ids: Optional[List[int]]

    discount_percent: Optional[float] 

    start_date: date
    end_date: date

class SKUSale(BaseModel):
    sku_id: int
    quantity: int = Field(ge=1)


class BundleSale(BaseModel):
    bundle_id: int
    quantity: int = Field(ge=1)


class Sale(BaseModel):
    sales_id: int

    customer_id: int

    promotion_ids: List[int]

    sale_date: date

    final_price: float = Field(ge=0)

    sku_sales: List[SKUSale]

    bundle_sales: List[BundleSale]