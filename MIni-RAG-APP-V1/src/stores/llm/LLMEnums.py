from enum import Enum

class LLMEnums(Enum):
  COHERE = "COHERE"
  OPENAI = "OPENAI"
  GEMINI = "GEMINI"

  

  
class OpenAIEnums(Enum):
  SYSTEM  = "system"
  USER = "user"
  ASSISTANT ="assistant"

class CohereEnums(Enum):
  SYSTEM  = "system"
  USER = "user"
  ASSISTANT ="assistant"

class GeminiEnums(Enum):
  SYSTEM  = "system"
  USER = "user"
  ASSISTANT ="model"

  DOCUMENT = "search_document"
  QUERY = "search_query"


class DocumentTypeEnum(Enum):
  DOCUMENT = "document"
  QUERY = "query"


