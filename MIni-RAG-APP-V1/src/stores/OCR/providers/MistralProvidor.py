import base64
import os
import re
from mistralai import Mistral
from ..OCRInterface import OCRInterface
from typing import List


class MistralProvidor(OCRInterface):
    def __init__(self, api_key: str, model_id: str, include_image_base64: bool = True):
        self.api_key = api_key
        self.model_id = model_id
        self.include_image_base64 = include_image_base64
        self.client = Mistral(api_key=api_key)

    def set_generation_model(self, model_id: str):
        self.model_id = model_id

    def _markdown_to_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text"""
        # Remove markdown formatting
        text = markdown_text
        
        # Remove headers (# ## ### etc.)
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove bold and italic (**text**, *text*)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Remove links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove code blocks and inline code
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove lists (* - +)
        text = re.sub(r'^[\s]*[-*+]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
        
        # Remove extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text

    def extract_text_from_pdf(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        try:
            # Read PDF file as bytes and convert to base64
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
            
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            # Process PDF directly with Mistral OCR
            response = self.client.ocr.process(
                model=self.model_id,
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                include_image_base64=self.include_image_base64,
            )
            
            # Extract text from all pages
            all_pages_text = []
            
            if response and hasattr(response, 'pages'):
                for i, page in enumerate(response.pages, start=1):
                    page_text = ""
                    
                    if hasattr(page, 'markdown'):
                        # Convert markdown to plain text
                        page_text = self._markdown_to_text(page.markdown)
                    elif hasattr(page, 'text'):
                        # Use plain text directly
                        page_text = page.text
                    
                    if page_text.strip():
                        all_pages_text.append(page_text)
            
            # Join all pages with separator
            return "\n\n---\n\n".join(all_pages_text) if all_pages_text else ""
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

        






