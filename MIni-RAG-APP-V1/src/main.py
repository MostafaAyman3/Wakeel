from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes import base, data, nlp
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await startup_span()
    yield
    # Shutdown logic
    await shutdown_span()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development. You can restrict this later.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def startup_span():
    settings = get_settings()
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings)

    # generation client
    app.state.generation_client = llm_provider_factory.create_provider(provider=settings.GENERATION_BACKEND)
    app.state.generation_client.set_generation_model(model_id = settings.GENERATION_MODEL_ID)

    # embedding client
    app.state.embedding_client = llm_provider_factory.create_provider(provider=settings.EMBEDDING_BACKEND)
    app.state.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID,
                                             model_dimension=settings.EMBEDDING_MODEL_SIZE)
    
    # vector db client
    app.state.vectordb_client = vectordb_provider_factory.create_provider(
        provider=settings.VECTOR_DB_BACKEND
    )
    await app.state.vectordb_client.connect()

    app.state.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )


async def shutdown_span():
    await app.state.vectordb_client.disconnect()

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)