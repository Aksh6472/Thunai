"""Shared DTO building blocks (API_SPEC §2)."""

from pydantic import BaseModel, ConfigDict


class RequestModel(BaseModel):
    """Every request body forbids unknown fields (mass-assignment guard, SECURITY T-08)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
