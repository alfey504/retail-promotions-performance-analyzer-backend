from typing import TypedDict,TypeVar, Generic

T = TypeVar("T")

class ResponseModel(TypedDict, Generic[T]):
    status: int
    message: str
    data: T

class PagedResponseModel(TypedDict, Generic[T]):
    status: int
    message: str
    max_page: int
    current_page: int
    data: T