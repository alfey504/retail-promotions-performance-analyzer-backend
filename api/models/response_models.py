from typing import TypedDict,TypeVar, Generic

T = TypeVar("T")

class ResponseModel(TypedDict, Generic[T]):
    status: int
    message: str
    data: T
