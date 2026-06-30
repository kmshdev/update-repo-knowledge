"""Classification constants for knowledge_diff.py."""

NO_DOC_NAMES = {
    ".DS_Store",
    "Cargo.lock",
    "Gemfile.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "yarn.lock",
}

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
