from .BaseController import BaseController
from .ProjectController import ProjectController
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from models.enums.ProcessingEnum import ProcessingEnum
from stores.OCR.OCRProvidorFactory import OCRProviderFactory
from helpers.config import get_settings
import os
import logging
from typing import List
from dataclasses import dataclass
from helpers.SupabaseStorageManager import SupabaseStorageManager
import tempfile

logger = logging.getLogger('uvicorn.error')

@dataclass
class Document:
    page_content: str
    metadata: dict


from langchain_text_splitters import RecursiveCharacterTextSplitter

class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)
        self.storage_manager = SupabaseStorageManager()
        
        # Initialize OCR provider
        self.settings = get_settings()
        self.ocr_factory = OCRProviderFactory(self.settings)
        self.ocr_provider = self.ocr_factory.create_provider(self.settings.OCR_BACKEND)


    def get_file_extension(self, file_id: str) -> str:
        return file_id.split('.')[-1]    
    
    def get_file_loader(self, file_id:str, file_path: str):
        file_ext = self.get_file_extension(file_id=file_id)
        
        logger.info(f"Loading file from temp path: {file_path}")

        file_ext_with_dot = f".{file_ext}"
        
        if file_ext_with_dot == ProcessingEnum.TEXT.value:
            return TextLoader(file_path, encoding='utf-8')
        
        if file_ext_with_dot == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        
        logger.error(f"Unsupported file extension: {file_ext_with_dot}")
        return None
    

    async def get_file_content(self, file_id: str, bucket_name: str, use_ocr: bool = True):
        # Download from Supabase
        try:
            file_bytes = await self.storage_manager.get_file_content(bucket_name, file_id)
        except Exception as e:
            logger.error(f"Failed to download file {file_id} from Supabase bucket {bucket_name}: {e}")
            return None

        file_ext = self.get_file_extension(file_id=file_id)
        file_ext_with_dot = f".{file_ext}"
        
        # Create a temporary file to work with existing loaders
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext_with_dot) as temp_file:
            temp_file.write(file_bytes)
            file_path = temp_file.name

        try:
            # Use OCR for PDF files if enabled
            if file_ext_with_dot == ProcessingEnum.PDF.value and use_ocr:
                try:
                    logger.info(f"Using OCR to extract text from PDF: {file_id}")
                    extracted_text = self.ocr_provider.extract_text_from_pdf(file_path)
                    
                    if extracted_text and extracted_text.strip():
                        return [Document(
                            page_content=extracted_text,
                            metadata={"source": file_id, "extraction_method": "ocr"}
                        )]
                    else:
                        logger.warning(f"OCR returned empty text for {file_id}, falling back to regular loader")
                except Exception as e:
                    logger.error(f"OCR extraction failed for {file_id}: {str(e)}, falling back to regular loader")
            
            # Fallback to regular loaders
            loader = self.get_file_loader(file_id=file_id, file_path=file_path)
            if loader is None:
                return None
            documents = loader.load()

            # Check for PDF page limit (1000 pages)
            if file_ext_with_dot == ProcessingEnum.PDF.value and len(documents) > 1000:
                logger.error(f"PDF exceeds 1000 page limit: {file_id}")
                return None
            
            # Convert to Document format if needed
            if documents and hasattr(documents[0], 'page_content'):
                return documents
            else:
                return [Document(
                    page_content=str(doc),
                    metadata={"source": file_id, "extraction_method": "loader"}
                ) for doc in documents]
        finally:
            # Clean up temp file
            if os.path.exists(file_path):
                os.remove(file_path)


    def process_file_content(self, file_content: list, file_id: str, chunk_size: int = 100, chunk_overlap: int = 20):
        # Join all parts of the file content (mostly for PDF pages)
        # Use double newline to maintain some separation between pages
        full_text = "\n\n".join([rec.page_content for rec in file_content])
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        split_chunks = text_splitter.split_text(full_text)
        
        chunks = [
            Document(
                page_content=chunk.strip(),
                metadata={"source": file_id}
            )
            for chunk in split_chunks if len(chunk.strip()) >= 10
        ]
        
        # Fallback if no chunks were created but there is content
        if not chunks and full_text.strip():
            chunks.append(Document(
                page_content=full_text.strip(),
                metadata={"source": file_id}
            ))

        return chunks

