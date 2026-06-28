from ..LLMInterface import LLMInterface
from ..LLMEnums import CohereEnums as CohereRoleEnums, DocumentTypeEnum
import cohere
import logging
from typing import List, Union

class CohereProvider(LLMInterface):
    def __init__(self, api_key: str, 
                  default_input_max_characters: int = 1000,
                  default_output_max_tokens: int = 1000,
                  default_generation_temperature: float = 0.1):

      self.api_key = api_key

      self.default_input_max_characters = default_input_max_characters
      self.default_output_max_tokens = default_output_max_tokens
      self.default_generation_temperature = default_generation_temperature

      self.generation_model_id = None

      self.embedding_model_id = None
      self.embedding_dimension = None

      self.client = cohere.Client(api_key = self.api_key)

      self.enums = CohereRoleEnums

      self.logger = logging.getLogger(__name__)


    def set_generation_model(self, model_id: str):
      self.generation_model_id = model_id
      self.logger.info(f"Set generation model to {model_id}")

    def set_embedding_model(self, model_id: str, model_dimension: int):
      self.embedding_model_id = model_id
      self.embedding_dimension = model_dimension
      self.logger.info(f"Set embedding model to {model_id} with dimension {model_dimension}")

    def  process_text(self, text: str):
      return text[:self.default_input_max_characters].strip()  

    async def generate_text(self, prompt: str, chat_history: list[dict],
                         max_output_tokens: int=None, temperature: float = None):
      if not self.client:
        raise ValueError("Cohere client not initialized") 

      if not self.generation_model_id:
        raise ValueError("Cohere generation model not set")

      max_output_tokens = max_output_tokens if max_output_tokens else self.default_output_max_tokens
      temperature = temperature if temperature else self.default_generation_temperature

      preamble = None
      cohere_history = []
      
      for msg in chat_history:
          role = msg.get("role")
          text = msg.get("message", "")
          if role == self.enums.SYSTEM.value:
              preamble = text
          else:
              # Cohere typically expects 'USER' and 'CHATBOT'
              cohere_role = "USER" if role == self.enums.USER.value else "CHATBOT"
              cohere_history.append({"role": cohere_role, "message": text})

      # Implement retry logic with exponential backoff for rate limiting
      import asyncio
      
      max_retries = 5
      base_delay = 1.0  # Start with 1 second delay for text generation
      
      for attempt in range(max_retries):
          try:
              # Add delay to respect rate limits
              await asyncio.sleep(base_delay)
              
              kwargs = {
                  "model": self.generation_model_id,
                  "message": prompt,
                  "temperature": temperature,
                  "max_tokens": max_output_tokens
              }
              
              if preamble:
                  kwargs["preamble"] = preamble
                  
              if cohere_history:
                  kwargs["chat_history"] = cohere_history

              response = self.client.chat(**kwargs)

              if not response or not response.text or len(response.text) == 0:
                  self.logger.error(f"Failed to generate text from Cohere. Response: {response}")
                  return None 

              return response.text
              
          except Exception as e:
              error_msg = str(e).lower()
              if "limit" in error_msg or "429" in error_msg or "quota" in error_msg or "rate" in error_msg:
                  if attempt < max_retries - 1:
                      # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                      delay = base_delay * (2 ** attempt)
                      self.logger.warning(f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                      await asyncio.sleep(delay)
                      continue
                  else:
                      self.logger.error(f"Max retries exceeded for text generation: {e}")
                      raise
              else:
                  # Non-rate-limit error, re-raise immediately
                  raise e
      
      return None

    async def generate_embedding(self, text: Union[str, list[str]],document_type: str = None):
      if not self.client:
        raise ValueError("Cohere client not initialized") 

      if isinstance(text, str):
        text = [text]

      if not self.embedding_model_id:
        raise ValueError("Cohere embedding model not set")

      # Process and filter out empty texts
      skip_filter = document_type == DocumentTypeEnum.QUERY.value
      processed_texts = []
      for t in text:
          if t:  # Check if original text is not None/empty
              processed_text = self.process_text(t).strip()
              # Filter out texts with less than 10 characters only if not a query
              if processed_text and (skip_filter or len(processed_text) >= 10):
                  processed_texts.append(processed_text)
      
      # Debug logging
      self.logger.info(f"Original text count: {len(text)}")
      self.logger.info(f"Processed text count: {len(processed_texts)}")
      if len(processed_texts) < len(text):
          self.logger.warning(f"Filtered out {len(text) - len(processed_texts)} empty texts")
      
      if not processed_texts:
        self.logger.error("No valid texts provided for embedding generation")
        return None

      input_type = "search_document"
      if document_type == DocumentTypeEnum.QUERY.value:
        input_type = "search_query"

      # Implement retry logic with exponential backoff for rate limiting
      import asyncio
      import time
      
      max_retries = 5
      base_delay = 2.0  # Start with 2 second delay to respect rate limits
      
      for attempt in range(max_retries):
          try:
              # Add delay to respect rate limits (100,000 tokens per minute)
              await asyncio.sleep(base_delay)
              
              response = self.client.embed(
                model=self.embedding_model_id,
                texts=processed_texts,
                input_type=input_type,
                embedding_types=["float"]
              )

              if not response or not response.embeddings or not response.embeddings.float or len(response.embeddings.float) == 0:
                  self.logger.error(f"Failed to generate embedding from Cohere. Response: {response}")
                  return None 

              return [f for f in response.embeddings.float]
              
          except Exception as e:
              error_msg = str(e).lower()
              if "limit" in error_msg or "429" in error_msg or "quota" in error_msg or "rate" in error_msg:
                  if attempt < max_retries - 1:
                      # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                      delay = base_delay * (2 ** attempt)
                      self.logger.warning(f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                      await asyncio.sleep(delay)
                      continue
                  else:
                      self.logger.error(f"Max retries exceeded for embedding generation: {e}")
                      raise
              else:
                  # Non-rate-limit error, re-raise immediately
                  raise e
      
      return None

    def construct_prompt(self, prompt: str, role: str):
      return {
        "role": role,
        "message":prompt
      }
      

