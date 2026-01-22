from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums (use when a small, finite set of values is allowed)
# ---------------------------------------------------------------------------


class InputMessageRole(StrEnum):
    USER = 'user'
    SYSTEM = 'system'
    DEVELOPER = 'developer'


class OutputMessageRole(StrEnum):
    ASSISTANT = 'assistant'


class ItemStatus(StrEnum):
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    INCOMPLETE = 'incomplete'


class ResponseStatus(StrEnum):
    COMPLETED = 'completed'
    FAILED = 'failed'
    IN_PROGRESS = 'in_progress'
    INCOMPLETE = 'incomplete'


class TruncationStrategy(StrEnum):
    AUTO = 'auto'
    DISABLED = 'disabled'


class SearchContextSize(StrEnum):
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'


class ReasoningEffort(StrEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class ResponseErrorCode(StrEnum):
    SERVER_ERROR = 'server_error'
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    INVALID_PROMPT = 'invalid_prompt'
    VECTOR_STORE_TIMEOUT = 'vector_store_timeout'
    INVALID_IMAGE = 'invalid_image'
    INVALID_IMAGE_FORMAT = 'invalid_image_format'
    INVALID_BASE64_IMAGE = 'invalid_base64_image'
    INVALID_IMAGE_URL = 'invalid_image_url'
    IMAGE_TOO_LARGE = 'image_too_large'
    IMAGE_TOO_SMALL = 'image_too_small'
    IMAGE_PARSE_ERROR = 'image_parse_error'
    IMAGE_CONTENT_POLICY_VIOLATION = 'image_content_policy_violation'
    INVALID_IMAGE_MODE = 'invalid_image_mode'
    IMAGE_FILE_TOO_LARGE = 'image_file_too_large'
    UNSUPPORTED_IMAGE_MEDIA_TYPE = 'unsupported_image_media_type'
    EMPTY_IMAGE_FILE = 'empty_image_file'
    FAILED_TO_DOWNLOAD_IMAGE = 'failed_to_download_image'
    IMAGE_FILE_NOT_FOUND = 'image_file_not_found'
