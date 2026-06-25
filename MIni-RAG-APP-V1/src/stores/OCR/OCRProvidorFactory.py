from .OCREnims import OCREnums
from stores.OCR.providers.MistralProvidor import MistralProvidor

class OCRProviderFactory:
  def __init__(self, config):
    self.config = config

  def create_provider(self, provider: str):

    if provider == OCREnums.MISTRAL.value:
      return MistralProvidor(
        api_key=self.config.MISTRAL_API_KEY,
        model_id=self.config.OCR_MODEL_ID,
        include_image_base64=True,
        

      )


