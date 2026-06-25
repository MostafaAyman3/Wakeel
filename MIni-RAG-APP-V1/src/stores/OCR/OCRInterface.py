from abc import ABC, abstractmethod
from typing import List


class OCRInterface(ABC):
    
    @abstractmethod
    def set_generation_model(self, model_id: str):
      pass
    
    @abstractmethod
    def extract_text_from_pdf(self, file_path: str) -> str:
      pass