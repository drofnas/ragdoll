"""LLM-backed worker services for embeddings and entity extraction."""

from ragdoll.platform.llm.chat import (
    ChatCompletionMessage,
    ChatCompletionService,
    DeterministicChatCompletionService,
    OllamaChatCompletionService,
    get_chat_completion_service,
)
from ragdoll.platform.llm.service import (
    DeterministicEmbeddingService,
    DeterministicEntityExtractionService,
    EmbeddingGenerationService,
    EntityExtractionError,
    EntityExtractionService,
    ExtractedEntityCandidate,
    OllamaEmbeddingService,
    OllamaEntityExtractionService,
    get_embedding_generation_service,
    get_entity_extraction_service,
    normalize_entity_name,
)

__all__ = [
    "ChatCompletionMessage",
    "ChatCompletionService",
    "DeterministicEmbeddingService",
    "DeterministicChatCompletionService",
    "DeterministicEntityExtractionService",
    "EmbeddingGenerationService",
    "EntityExtractionError",
    "EntityExtractionService",
    "ExtractedEntityCandidate",
    "OllamaEmbeddingService",
    "OllamaChatCompletionService",
    "OllamaEntityExtractionService",
    "get_chat_completion_service",
    "get_embedding_generation_service",
    "get_entity_extraction_service",
    "normalize_entity_name",
]
