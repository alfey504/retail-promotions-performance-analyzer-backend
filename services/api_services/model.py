from pydantic import BaseModel, Field
from typing import List, Generic, TypeVar
from pydantic import BaseModel, TypeAdapter
from typing import Optional, Literal
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
    product_description: Optional[str] = None
    product_brand: str
    product_category: str
 
 
class Sku(BaseModel):
    sku_id: int
    product_id: int
    sku_name: str
    size: Optional[str] = None
    color: Optional[str] = None
    last_fulfillment_date: Optional[date] = None
    next_fulfillment_date: Optional[date] = None
    in_stock: int = Field(ge=0)
    price: float = Field(gt=0)
 
 
class Customer(BaseModel):
    customer_id: int
    customer_age: int = Field(gt=0)
    customer_gender: str
    ethnicity: str
 
 
PromotionType = Literal["Percentage Off", "BOGO", "Flash Sale", "Seasonal Sale"]
 
 
class Promotion(BaseModel):
    promotion_id: int
    promotion_name: str
    promotion_description: Optional[str] = None
    promotion_type: PromotionType # type: ignore
    discount_percent: Optional[int] = None
    start_date: date
    end_date: date
    target_skus: list[int] = Field(min_length=1)
 

 
class FullfillmentHistory(BaseModel):
    fullfillment_id: int
    sku_id: int
    fullfillment_date: date
    quantity_received: int = Field(gt=0)
 
 
class Sale(BaseModel):
    sales_id: int
    sku_id: int
    promotion_id: Optional[int] = None
    regular_price: float = Field(gt=0)
    final_price: float = Field(gt=0)
    customer_id: Optional[int] = None 
    quantity: int = Field(gt=0)
    sale_date: date

 
ProductList = TypeAdapter(list[Product])
SkuList = TypeAdapter(list[Sku])
CustomerList = TypeAdapter(list[Customer])
PromotionList = TypeAdapter(list[Promotion])
FullfillmentHistoryList = TypeAdapter(list[FullfillmentHistory])
SaleList = TypeAdapter(list[Sale])
 
 