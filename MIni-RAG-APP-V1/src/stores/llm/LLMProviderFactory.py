from .LLMEnums import LLMEnums
from stores.llm.providers.OpenAIProvider import OpenAIProvider
from stores.llm.providers.CohereProvider import CohereProvider
from stores.llm.providers.GeminiProvider import GeminiProvider


class LLMProviderFactory:
  def __init__(self, config):
    self.config = config

  def create_provider(self, provider: str):

    if provider == LLMEnums.OPENAI.value:
      return OpenAIProvider(
        api_key=self.config.OPENAI_API_KEY,
        api_url=self.config.OPENAI_API_URL,
        default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
        default_output_max_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
        default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
      )

    elif provider == LLMEnums.COHERE.value:
      return CohereProvider(
        api_key=self.config.COHERE_API_KEY,
        default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
        default_output_max_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
        default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
      )

    elif provider == LLMEnums.GEMINI.value:
      return GeminiProvider(
        api_key=self.config.GEMINI_API_KEY,
        default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
        default_output_max_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
        default_generation_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
      )

    else:
      raise ValueError(f"Unsupported provider: {provider}")
