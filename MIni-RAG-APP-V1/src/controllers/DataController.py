import os
from .BaseController import BaseController
from fastapi import UploadFile
from models.enums.ResponseEnums import ResponseStatus
from .ProjectController import ProjectController
import re

class DataController(BaseController):
    def __init__(self):
        super().__init__()


    def validate_file(self, file: UploadFile) -> bool:
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseStatus.FILE_TYPE_NOT_SUPPORTED.value
        
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > self.app_settings.FILE_MAX_SIZE:
            return False, ResponseStatus.FILE_UPLOADED_FAILED.value # We could add a more specific signal later
    
        return True, ResponseStatus.FILE_UPLOADED_SUCCESSFULLY.value
    
    def generate_unique_file_path(self, original_file_name: str, project_id: str) -> str:
        random_key = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        clean_file_name = self.get_clean_file_name(original_file_name)
        new_file_name = f"{random_key}_{clean_file_name}"
        full_file_path = os.path.join(project_path, new_file_name)

        while os.path.exists(full_file_path):
            random_key = self.generate_random_string()
            new_file_name = f"{random_key}_{clean_file_name}"
            full_file_path = os.path.join(project_path, new_file_name)

        return full_file_path, f"{random_key}_{clean_file_name}"

    def  get_clean_file_name(self, original_file_name: str) -> str:
        clean_file_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', original_file_name)
        return clean_file_name
        

      