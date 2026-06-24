from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class OfferItem(BaseModel):
    """One supplier offer for a single RFQ."""
    vendor_name: str
    price_per_unit: float
    lead_time_days: Optional[int] = 14
    payment_terms: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("price_per_unit")
    @classmethod
    def positive_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price_per_unit must be positive")
        return v


class SubmitOffersRequest(BaseModel):
    rfq_id: UUID
    offers: list[OfferItem]
    language: Optional[str] = "en"

    @field_validator("offers")
    @classmethod
    def at_least_one(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one offer is required")
        return v


class OfferResult(BaseModel):
    offer_id: UUID
    vendor_name: str
    price_per_unit: float
    lead_time_days: Optional[int]


class RecommendedOffer(BaseModel):
    vendor_name: str
    price_per_unit: float
    lead_time_days: Optional[int]
    score: float
    justification: str


class SubmitOffersResponse(BaseModel):
    rfq_id: UUID
    offers_saved: int
    analysis_triggered: bool
    recommended_offer: Optional[RecommendedOffer] = None
    message: str


class OfferListItem(BaseModel):
    id: UUID
    rfq_id: UUID
    vendor_name: Optional[str] = None
    price_per_unit: float
    lead_time_days: Optional[int]
    payment_terms: Optional[str]
    received_at: datetime

    model_config = {"from_attributes": True}
