"""
--gb.ru/lessons/219762/homework
--mmankova

"""

from pydantic import BaseModel, Field

class OrderAssertion(BaseModel):
    iss: str
    sub: str
    aud: str
    jti: str
    exp: int
    iat: int

class AuthResponse(BaseModel):
    access_token: str
    expires_in: int = Field(default=3600)
    token_type: str = Field(default='Bearer')
    scope: str = Field(default='vehicles')
    refresh_token: str
