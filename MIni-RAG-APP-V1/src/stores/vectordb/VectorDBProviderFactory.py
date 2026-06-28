from .providers.SupabaseVectorProvider import SupabaseVectorProvider
from .VectorDBEnums import VectorDBEnums
from controllers.BaseController import BaseController


class VectorDBProviderFactory:
    def __init__(self, config, db_client: object = None):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create_provider(self, provider: str):
        if provider == VectorDBEnums.SUPABASE.value:
            return SupabaseVectorProvider(
                distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE or self.config.VECTOR_DB_DEFAULT_VECTOR_SIZE,
            )
        
        raise ValueError(f"Unsupported Vector DB provider: {provider}. This app is optimized for Supabase.")




