from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
import logging
from typing import List
from models.db_schemes import RetrievedDocument
from helpers.supabase_client import get_supabase_client

class SupabaseVectorProvider(VectorDBInterface):

    def __init__(self, default_vector_size: int = 768,
                       distance_method: str = "cosine"):
        
        self.supabase = get_supabase_client()
        self.default_vector_size = default_vector_size
        self.distance_method = distance_method
        self.logger = logging.getLogger("uvicorn")

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:
        # We check if chunks table exists and if there are records for this "collection" (project)
        return True # The chunks table is created via migration
    
    async def list_all_collections(self) -> List:
        try:
            res = self.supabase.table("chunks").select("chunk_project_id").execute()
            projects = set(item["chunk_project_id"] for item in res.data)
            return [f"collection_{self.default_vector_size}_{p}" for p in projects]
        except Exception:
            return []
    
    async def get_collection_info(self, collection_name: str) -> dict:
        project_id = self._extract_project_id(collection_name)
        try:
            res = self.supabase.table("chunks").select("*", count="exact").eq("chunk_project_id", project_id).execute()
            return {
                "record_count": res.count
            }
        except Exception:
            return None

    def _extract_project_id(self, collection_name: str) -> int:
        try:
            # collection_1024_5 -> 5
            return int(collection_name.split('_')[-1])
        except Exception:
            return 0
            
    async def delete_collection(self, collection_name: str):
        project_id = self._extract_project_id(collection_name)
        try:
            self.logger.info(f"Resetting vectors for project: {project_id}")
            res = self.supabase.table("chunks").update({"vector": None}).eq("chunk_project_id", project_id).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error resetting vectors for {collection_name}: {e}")
            return False

    async def create_collection(self, collection_name: str,
                                       embedding_size: int,
                                       do_reset: bool = False):
        if do_reset:
            await self.delete_collection(collection_name)
        return True
    
    async def insert_one(self, collection_name: str, text: str, vector: list,
                            metadata: dict = None,
                            record_id: int = None):
        project_id = self._extract_project_id(collection_name)
        data = {
            "chunk_text": text,
            "vector": vector,
            "chunk_metadata": metadata,
            "chunk_project_id": project_id
            # chunk_id is the primary key and is auto-generated or passed. 
            # In ChunkModel.insert_many_chunks, it's already handled.
        }
        res = self.supabase.table("chunks").insert(data).execute()
        return bool(res.data)
    

    async def insert_many(self, collection_name: str, texts: list,
                         vectors: list, metadata: list = None,
                         record_ids: list = None, batch_size: int = 50):
        project_id = self._extract_project_id(collection_name)
        
        # If we have record_ids, it means we are updating existing chunks (e.g. during Push)
        # We use individual updates to avoid violates not-null constraint on columns we don't provide
        if record_ids:
            self.logger.info(f"Updating {len(record_ids)} existing chunks with vectors.")
            for i in range(len(record_ids)):
                try:
                    self.supabase.table("chunks").update({
                        "vector": vectors[i]
                    }).eq("chunk_id", record_ids[i]).execute()
                except Exception as e:
                    self.logger.error(f"Failed to update chunk {record_ids[i]}: {e}")
            return True

        # Otherwise, handles as new insertions
        data = []
        for i in range(len(texts)):
            item = {
                "chunk_text": texts[i],
                "vector": vectors[i],
                "chunk_metadata": metadata[i] if metadata else {},
                "chunk_project_id": project_id
            }
            data.append(item)
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            self.supabase.table("chunks").insert(batch).execute()

        return True
    
    async def search_by_vector(self, collection_name: str, vector: list, limit: int):
        project_id = self._extract_project_id(collection_name)
        params = {
            "query_embedding": vector,
            "match_threshold": 0.0,
            "match_count": limit,
            "target_table_name": "chunks",
            "filter_project_id": project_id
        }
        
        try:
            res = self.supabase.rpc("match_vectors", params).execute()
        except Exception as e:
            self.logger.error(f"Error calling match_vectors RPC: {e}")
            return []
        
        results = []
        if res.data:
            for item in res.data:
                meta = item.get("chunk_metadata") or {}
                source = meta.get("source") if isinstance(meta, dict) else None
                results.append(RetrievedDocument(
                    text=item.get("chunk_text", item.get("text")),
                    score=item["score"],
                    source=source,
                ))
        return results
