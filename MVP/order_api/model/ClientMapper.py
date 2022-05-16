"""
--gb.ru/lessons/219762/homework
--mmankova

"""

from pydantic import BaseModel, Field

class ClientAssertion(BaseModel):
    client_id: int
    name: str
    adress: str

class ClientResponse(BaseModel):
    client_id: int = Field(default=3600)
    name: str= Field()
    adress: str= Field()
