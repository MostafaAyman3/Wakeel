from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from uuid import UUID

class AnalyzeRequest(BaseModel):
    trigger_source: str = "manual"
    language: str = "ar-EG"

class AlertData(BaseModel):
    alert_id: str
    product_id: str
    alert_type: str
    metadata: Dict[str, Any]

class RFQDraftData(BaseModel):
    rfq_id: str
    product_id: str
    draft_text: str

class PricingRecData(BaseModel):
    product_id: str
    recommendation: str

class AnalyzeResponse(BaseModel):
    scan_summary: Dict[str, Any]
    alerts: List[AlertData] = []
    rfq_drafts: List[RFQDraftData] = []
    pricing_recs: List[PricingRecData] = []
    language: str
