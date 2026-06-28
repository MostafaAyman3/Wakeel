from fastapi import APIRouter, FastAPI, Depends, UploadFile, status, Request, File
from fastapi.responses import JSONResponse
from typing import Annotated
import os
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController
import aiofiles
from models.enums.ResponseEnums import ResponseStatus
import logging
from .schemas.data import ProcessRequest

logger = logging.getLogger("uvicorn.error")

from controllers.ProcessController import ProcessController
from models.ProjectModel import ProjectModel
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum
from controllers.NLPController import NLPController
from helpers.SupabaseStorageManager import SupabaseStorageManager
from stores.llm.LLMEnums import DocumentTypeEnum
data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, file: UploadFile = File(None), app_settings: Settings = Depends(get_settings)):
    if file is None:
        form = await request.form()
        logger.error(f"File field missing in request. Available keys: {list(form.keys())}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            content={
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["body", "file"],
                        "msg": "Field required",
                        "input": None
                    }
                ]
            }
        )
    
    project_model = await ProjectModel.create_instance()
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_file(file=file)

    if not is_valid:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": result_signal, "message": "File validation failed."})


    project_dir_path = ProjectController().get_project_path(project_id=str(project_id))
    # os.makedirs(project_dir_path, exist_ok=True) # Likely not needed for Supabase mode, but keeping for path generation
    
    file_path, file_id = data_controller.generate_unique_file_path(original_file_name=file.filename, project_id=str(project_id))
    
    try:
        file_content = await file.read()
        storage_manager = SupabaseStorageManager()
        upload_result = await storage_manager.upload_file(
            file=file_content,
            file_name=file_id,
            content_type=file.content_type
        )
    except Exception as e:
        logger.error(f"Error uploading file to Supabase: {e}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": ResponseStatus.FILE_UPLOADED_FAILED.value, "message": str(e)})


    asset_model = await AssetModel.create_instance()
    
    asset_record = await asset_model.create_asset(
      asset_project_id = project["project_id"],
      asset_type = AssetTypeEnum.FILE.value,
      asset_name = file_id,
      asset_size = 0, # Cannot easily get size from stream without reading, set to 0 or use file.size if available (often not for stream)
      asset_config = {"bucket": upload_result["bucket"]}
    )

    return JSONResponse(content={
      "signal": ResponseStatus.FILE_UPLOADED_SUCCESSFULLY.value, 
      "file_id": asset_record["asset_name"]
    })

@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest, app_settings: Settings = Depends(get_settings)):  
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    project_model = await ProjectModel.create_instance()
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.state.vectordb_client,
        generation_client=request.app.state.generation_client,
        embedding_client=request.app.state.embedding_client,
        template_parser=request.app.state.template_parser
    )

    asset_model = await AssetModel.create_instance()

    project_file_ids = {}   
    if process_request.file_id:
      asset_record = await asset_model.get_asset_record(asset_project_id=project["project_id"], asset_name=process_request.file_id)
      if asset_record is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": ResponseStatus.FILE_ID_ERROR.value, "message": "File not found with this id."})
      project_file_ids = {asset_record["asset_id"]:asset_record["asset_name"]}
    else:
        project_files = await asset_model.get_all_project_assets(asset_project_id=project["project_id"], asset_type=AssetTypeEnum.FILE.value)
        project_file_ids = {record["asset_id"]:record["asset_name"] for record in project_files}

    if len(project_file_ids) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"signal": ResponseStatus.FILE_NOT_FOUND.value, "message": "File not found."})

    logger.info(f"Processing {len(project_file_ids)} files in project: {project_id}")
    
    process_controller = ProcessController(project_id=str(project_id))
    
    # Delegating logic to NLPController
    num_records, num_files = await nlp_controller.process_project_files(
        project=project,
        file_ids=project_file_ids,
        do_reset=do_reset,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        process_controller=process_controller
    )
          
    return JSONResponse(content={"signal": ResponseStatus.FILE_PROCESSED_SUCCESSFULLY.value, "inserted_chunks": num_records, "processed_files": num_files})
