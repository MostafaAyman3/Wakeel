from pydantic import BaseModel
from typing import Optional

class RetrievedDocument(BaseModel):
    text: str
    score: float
    source: Optional[str] = None  # originating document name (from chunk_metadata)
