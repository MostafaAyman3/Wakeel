from .BaseController import BaseController
from typing import List
from stores.llm.LLMEnums import DocumentTypeEnum
import logging
import json

from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel


class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                 embedding_client, template_parser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.logger = logging.getLogger(__name__)

    def create_collection_name(self, project_id: int):
        collection_name = f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()
        return collection_name
    
    async def reset_vector_db_collection(self, project: dict):
        collection_name = self.create_collection_name(project_id=project["project_id"])
        return await self.vectordb_client.delete_collection(collection_name=collection_name)
    
    async def get_vector_db_collection_info(self, project: dict):
        collection_name = self.create_collection_name(project_id=project["project_id"])
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)

        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )
    
    async def index_into_vector_db(self, project: dict, chunks: List[dict],
                                   chunks_ids: List[int], 
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project["project_id"])

        # step2: manage items
        # Filter out chunks with less than 10 characters
        valid_chunks = [c for c in chunks if c.get("chunk_text") and len(c["chunk_text"].strip()) >= 10]
        
        texts = [c["chunk_text"] for c in valid_chunks]
        metadata = [c.get("chunk_metadata", {}) for c in valid_chunks]
        
        self.logger.info(f"Total chunks to process: {len(chunks)}")
        self.logger.info(f"Valid chunks after filtering: {len(valid_chunks)}")
        
        if texts:
            vectors = await self.embedding_client.generate_embedding(text=texts, 
                                                 document_type=DocumentTypeEnum.DOCUMENT.value)

            if not vectors:
                self.logger.error("Failed to generate embeddings for chunks")
                return False

            # step3: create collection if not exists
            _ = await self.vectordb_client.create_collection(
                collection_name=collection_name,
                embedding_size=self.embedding_client.embedding_dimension,
                do_reset=do_reset,
            )

            # step4: insert into vector db
            _ = await self.vectordb_client.insert_many(
                collection_name=collection_name,
                texts=texts,
                metadata=metadata,
                vectors=vectors,
                record_ids=chunks_ids,
            )

        return True

    async def search_vector_db_collection(self, project: dict, text: str, limit: int = 10):

        # step1: get collection name
        query_vector = None
        collection_name = self.create_collection_name(project_id=project["project_id"])

        # step2: get text embedding vector
        vectors = await self.embedding_client.generate_embedding(text=text, 
                                                 document_type=DocumentTypeEnum.QUERY.value)

        if not vectors or len(vectors) == 0:
            return False

        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return False

        # step3: do semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit
        )

        if results is None:
            return False

        return results
    
    @staticmethod
    def _clean_source_name(raw: str) -> str:
        """Strip the random upload prefix (e.g. 'uudl5njtlq87_faq.txt' -> 'faq.txt')."""
        if not raw:
            return raw
        return raw.split("_", 1)[1] if "_" in raw else raw

    async def answer_rag_question(self, project: dict, query: str, limit: int = 10, chat_history: list = None):

        answer, full_prompt, llm_chat_history = None, None, None

        # step1: retrieve related documents
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, llm_chat_history, []

        # Distinct, human-friendly source names from the retrieved chunks (Fix 4)
        sources = []
        for doc in retrieved_documents:
            name = self._clean_source_name(getattr(doc, "source", None) or "")
            if name and name not in sources:
                sources.append(name)
        
        # step2: Construct LLM prompt
        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "chunk_text": self.generation_client.process_text(doc.text),
            })
            for idx, doc in enumerate(retrieved_documents)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt")

        # step3: Construct Generation Client Prompts
        llm_chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        if chat_history:
            for msg in chat_history:
                role_value = self.generation_client.enums.USER.value if msg.get("role") == "user" else self.generation_client.enums.ASSISTANT.value
                llm_chat_history.append(
                    self.generation_client.construct_prompt(
                        prompt=msg.get("content", ""),
                        role=role_value
                    )
                )

        user_question_prompt = self.template_parser.get("rag", "user_question_prompt", {
            "user_query": query
        })

        full_prompt = "\n\n".join([ documents_prompts, user_question_prompt, footer_prompt])

        # step4: Retrieve the Answer
        answer = await self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=llm_chat_history
        )


        return answer, full_prompt, llm_chat_history, sources

    async def process_project_files(self, project: dict, file_ids: dict, do_reset: int,
                                    chunk_size: int, overlap_size: int, process_controller: object):
        
        num_records = 0
        processed_files = 0
        
        chunk_model = await ChunkModel.create_instance()

        if do_reset == 1:
            await self.reset_vector_db_collection(project=project)
            _ = await chunk_model.delete_chunks_by_project_id(project_id=project["project_id"])

        asset_model = await AssetModel.create_instance()

        for asset_id, file_id in file_ids.items():
            
            # Dynamic bucket fetching
            asset_record = await asset_model.get_asset_record(asset_project_id=project["project_id"], asset_name=file_id)
            bucket_name = "fields1" # Default
            if asset_record and asset_record.get("asset_config"):
                bucket_name = asset_record["asset_config"].get("bucket", "fields1")

            file_content = await process_controller.get_file_content(
                file_id=file_id, 
                bucket_name=bucket_name,
                use_ocr=self.app_settings.OCR_ENABLED
            )
            
            if not file_content:
                self.logger.warning(f"Skipping file {file_id}: Could not extract content or file not found in Supabase ({bucket_name})")
                continue

            
            chunks = process_controller.process_file_content(
                file_content=file_content,
                file_id=file_id,
                chunk_size=chunk_size,
                chunk_overlap=overlap_size
            )

            if not chunks:
                self.logger.error(f"File processing failed for: {file_id}")
                continue

            self.logger.info(f"Successfully processed file: {file_id} into {len(chunks)} chunks")
            
            file_chunks_data = [
                {
                    "chunk_text": chunk.page_content,
                    "chunk_metadata": chunk.metadata,
                    "chunk_order": i+1,
                    "chunk_project_id": project["project_id"],
                    "chunk_asset_id": asset_id
                }
                for i, chunk in enumerate(chunks)
            ]
            
            # Generate vectors
            vectors = await self.embedding_client.generate_embedding(
                text=[c["chunk_text"] for c in file_chunks_data],
                document_type=DocumentTypeEnum.DOCUMENT.value
            )
            
            # Add vectors to chunks for Supabase
            if self.app_settings.VECTOR_DB_BACKEND == "SUPABASE":
                for i, vector in enumerate(vectors):
                    file_chunks_data[i]["vector"] = vector


            # Insert into SQL Table (Supabase)
            inserted_chunks = await chunk_model.insert_many_chunks(file_chunks_data)
            num_records += len(inserted_chunks) if inserted_chunks else 0
            
            processed_files += 1

        return num_records, processed_files

