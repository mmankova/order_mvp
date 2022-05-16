"""
--gb.ru/lessons/219762/homework
--mmankova

"""

from pydantic import BaseModel, Field

class RestaurantAssertion(BaseModel):
    restaurant_id: int
    name: str
    rating: str

class RestaurantResponse(BaseModel):
    restaurant_id: int = Field(default=3600)
    name: str = Field()
    rating: str= Field()
