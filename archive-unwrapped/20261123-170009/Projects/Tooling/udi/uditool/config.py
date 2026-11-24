import re

CANONICAL_KINDS = [
    "api-ref",
    "ast-node",
    "capability",
    "chroma-scheme",
    "colour-keys",
    "colour-roles",
    "colour-scheme",
    "composition",
    "config",
    "document",
    "function-ref",
    "log-file",
    "manifest",
    "menu",
    "menu-item",
    "metadata",
    "pane",
    "pane-roles",
    "registry",
    "scan-result",
    "schema",
    "service",
    "search-result",
    "ui-framework",
]

CANONICAL_NAMESPACES = ["prismata", "lumen", "nebula"]

UDI_REGEX = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]+$")

FOLDER_SCOPE_MAP = {
    "Meta/canonical": "meta",
    "ui-framework": "ui-framework",
    "colour-schemes": "colour-scheme",
    "chroma-schemes": "chroma-scheme",
    "pane": "pane",
    "pane-roles": "pane-roles",
    "registry": "registry",
    "log-files": "log-file",
}

DETECTOR_VERSION = "1.1.0"
