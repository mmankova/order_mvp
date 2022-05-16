"""
--gb.ru/lessons/219762/homework
--mmankova

"""

from datetime import datetime
from pydantic import BaseModel, Field

class OrderMapperAssertion(BaseModel):
    order_id: int
    name: str 
    creation_time: datetime
    modification_time: datetime
    status_id: int
    payment_method: str
    rating: int
    client_id: int
    restaurant_id: int
    delivery_id: int

class AuthResponse(BaseModel):
    order_id: int = Field()
    name: str  = Field()
    creation_time: datetime = Field()
    modification_time: datetime = Field()
    status_id: int = Field()
    payment_method: str = Field()
    rating: int = Field()
    client_id: int = Field()
    restaurant_id: int = Field()
    delivery_id: int = Field()
