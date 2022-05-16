"""
--gb.ru/lessons/219762/homework
--mmankova

"""

from pydantic import BaseModel, Field

class DeliveryMapperAssertion(BaseModel):
    delivery_id : int
    name: str
    rating: str

class DeliveryMapperResponse(BaseModel):
    delivery_id: int = Field()
    name: str = Field()
    rating: str = Field()
