from .BaseDataModel import BaseDataModel
from .enums.DataBaseEnum import DataBaseEnum

class ChunkModel(BaseDataModel):

    def __init__(self):
        super().__init__()
        self.table_name = DataBaseEnum.COLLECTION_CHUNKS.value

    @classmethod
    async def create_instance(cls, db_client: object = None):
        instance = cls()
        return instance

    async def create_chunk(self, chunk_text: str, chunk_metadata: dict, chunk_order: int, chunk_project_id: int, chunk_asset_id: int):
        data = {
            "chunk_text": chunk_text,
            "chunk_metadata": chunk_metadata,
            "chunk_order": chunk_order,
            "chunk_project_id": chunk_project_id,
            "chunk_asset_id": chunk_asset_id
        }
        res = self.supabase.table(self.table_name).insert(data).execute()
        if res.data:
            return res.data[0]
        return None

    async def get_chunk(self, chunk_id: int):
        res = self.supabase.table(self.table_name).select("*").eq("chunk_id", chunk_id).execute()
        if res.data:
            return res.data[0]
        return None

    async def insert_many_chunks(self, chunks_data: list):
        # chunks_data should be a list of dicts reflecting the table schema
        res = self.supabase.table(self.table_name).insert(chunks_data).execute()
        return res.data

    async def delete_chunks_by_project_id(self, project_id: int):
        res = self.supabase.table(self.table_name).delete().eq("chunk_project_id", project_id).execute()
        return len(res.data) if res.data else 0
    
    async def get_project_chunks(self, project_id: int, page_no: int=1, page_size: int=5):
        offset = (page_no - 1) * page_size
        res = self.supabase.table(self.table_name).select("*").eq("chunk_project_id", project_id).range(offset, offset + page_size - 1).execute()
        return res.data

    async def get_total_chunks_coumt(self, project_id: int):
        res = self.supabase.table(self.table_name).select("*", count="exact").eq("chunk_project_id", project_id).execute()
        return res.count if res.count is not None else 0


