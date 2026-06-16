"""Shared package publish limits used by CLI and server validation."""

MAX_PACKAGE_FILES = 128
MAX_PACKAGE_PATH_LENGTH = 240
MAX_PACKAGE_FILE_BYTES = 256 * 1024
MAX_PACKAGE_TOTAL_BYTES = 1024 * 1024

# Request bodies are checked before JSON parsing, so the cap must allow a package
# that is valid by content limits even when every content byte is escaped as a
# JSON control character (`\u00XX`). UTF-8 scalar escaping is cheaper per content
# byte (for example, a 4-byte code point becomes a 12-byte surrogate-pair escape).
JSON_CONTROL_ESCAPE_BYTES_PER_CONTENT_BYTE = len("\\u001f")

# File paths are limited by Python string length, not UTF-8 bytes. A single path
# character can be encoded as two JSON UTF-16 surrogate escapes (`\uXXXX\uXXXX`).
JSON_SURROGATE_ESCAPE_BYTES_PER_PATH_CHAR = len("\\ud83d\\ude00")

# Compact JSON syntax overhead for {"files":{"path":"content",...}}. The entry
# syntax includes one comma per file as a deliberate one-byte overestimate.
PACKAGE_PUBLISH_JSON_ENVELOPE_BYTES = len('{"files":{}}')
PACKAGE_PUBLISH_JSON_FILE_ENTRY_SYNTAX_BYTES = len('"":""') + len(",")

MAX_PACKAGE_PUBLISH_CONTENT_JSON_BYTES = (
    MAX_PACKAGE_TOTAL_BYTES * JSON_CONTROL_ESCAPE_BYTES_PER_CONTENT_BYTE
)
MAX_PACKAGE_PUBLISH_PATH_JSON_BYTES = (
    MAX_PACKAGE_FILES
    * MAX_PACKAGE_PATH_LENGTH
    * JSON_SURROGATE_ESCAPE_BYTES_PER_PATH_CHAR
)
MAX_PACKAGE_PUBLISH_JSON_SYNTAX_BYTES = PACKAGE_PUBLISH_JSON_ENVELOPE_BYTES + (
    MAX_PACKAGE_FILES * PACKAGE_PUBLISH_JSON_FILE_ENTRY_SYNTAX_BYTES
)
MAX_PACKAGE_PUBLISH_BODY_BYTES = (
    MAX_PACKAGE_PUBLISH_CONTENT_JSON_BYTES
    + MAX_PACKAGE_PUBLISH_PATH_JSON_BYTES
    + MAX_PACKAGE_PUBLISH_JSON_SYNTAX_BYTES
)
