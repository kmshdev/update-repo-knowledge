"""Constants for ast_change_hints.py."""

from __future__ import annotations

import re


NOTE = "AST hints identify touched structures only; inspect source/tests before updating docs."

HUNK_PATTERN = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

NO_DOC_SUFFIXES = {
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
}

NO_DOC_PATH_PARTS = {
    ".cache",
    "__pycache__",
    "coverage",
    "dist",
    "generated",
    "node_modules",
}

LANGUAGE_BY_EXTENSION = {
    ".bash": "bash",
    ".bats": "bash",
    ".c": "c",
    ".cc": "cpp",
    ".cjs": "javascript",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".cxx": "cpp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".go": "go",
    ".h": "c",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".hs": "haskell",
    ".htm": "html",
    ".html": "html",
    ".hxx": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".mjs": "javascript",
    ".php": "php",
    ".phtml": "php",
    ".py": "python",
    ".pyw": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sc": "scala",
    ".scala": "scala",
    ".sh": "bash",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".yaml": "yaml",
    ".yml": "yaml",
}

LANGUAGE_BY_NAME = {
    "bashrc": "bash",
}

KIND_PROFILES = {
    "bash": ["function_definition"],
    "c": ["function_definition", "struct_specifier", "enum_specifier"],
    "cpp": ["function_definition", "class_specifier", "struct_specifier", "enum_specifier"],
    "csharp": ["class_declaration", "method_declaration", "struct_declaration"],
    "css": ["rule_set", "at_rule"],
    "elixir": ["call"],
    "go": ["function_declaration", "method_declaration", "type_declaration"],
    "haskell": ["function", "type_alias", "data_type"],
    "html": ["element", "script_element", "style_element"],
    "java": ["class_declaration", "method_declaration", "interface_declaration"],
    "javascript": ["function_declaration", "class_declaration", "method_definition"],
    "json": ["object", "pair", "array"],
    "kotlin": ["function_declaration", "class_declaration", "object_declaration"],
    "lua": ["function_declaration", "function_definition"],
    "php": ["function_definition", "class_declaration", "method_declaration"],
    "python": ["function_definition", "class_definition", "decorated_definition"],
    "ruby": ["method", "class", "module"],
    "rust": ["function_item", "struct_item", "enum_item", "impl_item", "trait_item"],
    "scala": ["function_definition", "class_definition", "object_definition", "trait_definition"],
    "swift": [
        "function_declaration",
        "class_declaration",
        "struct_declaration",
        "enum_declaration",
    ],
    "typescript": ["function_declaration", "class_declaration", "method_definition"],
    "tsx": ["function_declaration", "class_declaration", "method_definition"],
    "yaml": ["block_mapping_pair", "block_mapping", "block_sequence_item"],
}
