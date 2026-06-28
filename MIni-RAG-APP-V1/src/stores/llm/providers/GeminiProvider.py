from ..LLMInterface import LLMInterface
from ..LLMEnums import GeminiEnums as GeminiRoleEnums, DocumentTypeEnum
from google import genai
from google.genai import types
import logging
from typing import Union, List

class GeminiProvider(LLMInterface):
    def __init__(self, api_key: str, 
                  default_input_max_characters: int = 1000000,
                  default_output_max_tokens: int = 8192,
                  default_generation_temperature: float = 0.7):

      self.api_key = api_key

      self.default_input_max_characters = default_input_max_characters
      self.default_output_max_tokens = default_output_max_tokens
      self.default_generation_temperature = default_generation_temperature

      self.generation_model_id = None

      self.embedding_model_id = None
      self.embedding_dimension = None

      self.client = genai.Client(api_key=self.api_key)

      self.enums = GeminiRoleEnums

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

    def generate_text(self, prompt: str, chat_history: list[dict],
                         max_output_tokens: int=None, temperature: float = None):
      if not self.generation_model_id:
        raise ValueError("Gemini generation model not set")

      max_output_tokens = max_output_tokens if max_output_tokens else self.default_output_max_tokens
      temperature = temperature if temperature else self.default_generation_temperature

      # Convert chat history to Gemini format
      contents = []
      system_instruction_text = None
      for message in chat_history:
        role = message.get("role")
        text_content = message.get("parts", [{}])[0].get("text", "")
        if role == self.enums.SYSTEM.value:
          system_instruction_text = text_content
          continue
        
        # Ensure role is valid for Gemini (user or model)
        if role not in ["user", "model"]:
            role = "user" # Fallback if somehow an invalid role is present
            
        contents.append(types.Content(role=role, parts=[types.Part(text=text_content)]))
      
      # Add current prompt without truncating it (process_text truncates to 1024 chars by default)
      contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

      config = types.GenerateContentConfig(
          temperature=temperature,
          max_output_tokens=max_output_tokens,
      )
      
      if system_instruction_text:
          config.system_instruction = system_instruction_text

      response = self.client.models.generate_content(
          model=self.generation_model_id,
          contents=contents,
          config=config
      )

      if not response:
        self.logger.error("Failed to generate text from Gemini - no response")
        return None

      try:
        if response.text:
          return response.text
      except Exception as e:
        self.logger.error(f"Error extracting text from Gemini response: {e}")
        
      self.logger.error(f"Failed to extract text from Gemini response: {response}")
      return None

    async def generate_embedding(self, text: Union[str, list[str]], document_type: str = None):
      if not self.embedding_model_id:
        raise ValueError("Gemini embedding model not set")

      if isinstance(text, str):
        text = [text]

      # Use appropriate task_type based on document_type
      task_type = "RETRIEVAL_DOCUMENT"
      if document_type == DocumentTypeEnum.QUERY.value:
        task_type = "RETRIEVAL_QUERY"

      # Use output_dimensionality parameter to control embedding size
      output_dimensionality = self.embedding_dimension
      if output_dimensionality > 2000:
        output_dimensionality = 1536  # Use a size compatible with HNSW
        self.logger.warning(f"Reducing embedding dimension from {self.embedding_dimension} to {output_dimensionality} for HNSW compatibility")

      # Implement retry logic with exponential backoff for rate limiting
      import asyncio
      
      max_retries = 5
      base_delay = 2.0  # Start with 2 second delay to be more conservative
      
      for attempt in range(max_retries):
          try:
              # Add longer delay to respect rate limits
              await asyncio.sleep(base_delay)
              
              response = self.client.models.embed_content(
                  model=self.embedding_model_id,
                  contents=[self.process_text(t) for t in text],
                  config=types.EmbedContentConfig(
                      task_type=task_type,
                      output_dimensionality=output_dimensionality
                  )
              )

              if not response or not hasattr(response, 'embeddings') or len(response.embeddings) == 0:
                  self.logger.error(f"Failed to generate embedding from Gemini. Response: {response}")
                  return None

              # The new SDK returns a list of embeddings
              embedding = response.embeddings[0].values
              
              # Update the actual embedding dimension to match what was generated
              actual_dimension = len(embedding)
              if actual_dimension != self.embedding_dimension:
                  self.logger.info(f"Actual embedding dimension: {actual_dimension} (configured: {self.embedding_dimension})")
                  self.embedding_dimension = actual_dimension

              # Truncate embedding if it's too large for HNSW (though output_dimensionality should handle this)
              if len(embedding) > 2000:
                  embedding = embedding[:1536]  # Truncate to 1536 dimensions
                  self.logger.warning(f"Truncated embedding from {len(embedding)} to 1536 dimensions for HNSW compatibility")
                  self.embedding_dimension = len(embedding)

              return [embedding]
              
          except Exception as e:
              if "quota" in str(e).lower() or "429" in str(e):
                  if attempt < max_retries - 1:
                      delay = base_delay * (2 ** attempt)
                      self.logger.warning(f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                      await asyncio.sleep(delay)
                      continue
                  else:
                      self.logger.error(f"Max retries exceeded for embedding generation: {e}")
                      raise
              else:
                  raise e
      
      return None

    def construct_prompt(self, prompt: str, role: str):
      return {
        "role": role,
        "parts": [{"text": prompt}]
      }
