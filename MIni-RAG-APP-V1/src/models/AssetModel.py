from .BaseDataModel import BaseDataModel
from .enums.DataBaseEnum import DataBaseEnum

class AssetModel(BaseDataModel):

    def __init__(self):
        super().__init__()
        self.table_name = DataBaseEnum.COLLECTION_ASSETS.value

    @classmethod
    async def create_instance(cls, db_client: object = None):
        instance = cls()
        return instance

    async def create_asset(self, asset_project_id: int, asset_type: str, asset_name: str, asset_size: int, asset_config: dict):
        data = {
            "asset_project_id": asset_project_id,
            "asset_type": asset_type,
            "asset_name": asset_name,
            "asset_size": asset_size,
            "asset_config": asset_config
        }
        res = self.supabase.table(self.table_name).insert(data).execute()
        if res.data:
            return res.data[0]
        return None

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str):
        res = self.supabase.table(self.table_name).select("*").eq("asset_project_id", asset_project_id).eq("asset_type", asset_type).execute()
        return res.data

    async def get_asset_record(self, asset_project_id: int, asset_name: str):
        res = self.supabase.table(self.table_name).select("*").eq("asset_project_id", asset_project_id).eq("asset_name", asset_name).execute()
        if res.data:
            return res.data[0]
        return None


    