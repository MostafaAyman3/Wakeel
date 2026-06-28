from .BaseDataModel import BaseDataModel
from .enums.DataBaseEnum import DataBaseEnum

class ProjectModel(BaseDataModel):
    def __init__(self):
        super().__init__()
        self.table_name = DataBaseEnum.COLLECTION_PROJECTS.value

    @classmethod
    async def create_instance(cls, db_client: object = None):
        # db_client is no longer needed but kept for signature compatibility if used elsewhere
        instance = cls()
        return instance

    async def create_project(self, project_id: int):
        data = {
            "project_id": project_id
        }
        res = self.supabase.table(self.table_name).insert(data).execute()
        if res.data:
            return res.data[0]
        return None

    async def get_project_or_create_one(self, project_id: int):
        res = self.supabase.table(self.table_name).select("*").eq("project_id", project_id).execute()
        if res.data:
            return res.data[0]
        
        return await self.create_project(project_id=project_id)

    async def get_all_projects(self, page: int=1, page_size: int=10):
        # Get count
        count_res = self.supabase.table(self.table_name).select("*", count="exact").execute()
        total_documents = count_res.count if count_res.count is not None else 0

        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1

        offset = (page - 1) * page_size
        projects_res = self.supabase.table(self.table_name).select("*").range(offset, offset + page_size - 1).execute()
        
        return projects_res.data, total_pages
