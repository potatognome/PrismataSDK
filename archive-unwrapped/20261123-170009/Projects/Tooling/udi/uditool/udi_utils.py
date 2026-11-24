import re
import unicodedata
from .config import UDI_REGEX, CANONICAL_KINDS, CANONICAL_NAMESPACES


def slugify(name: str) -> str:
    if not name:
        return ""
    s = name.strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s[:64]


def normalize_scope(scope: str) -> str:
    """Normalize a folder/scope name into a canonical scope token.

    Rules:
    - Split on dot, slash or backslash into tokens.
    - Singularize simple plural endings (drop trailing 's').
    - Join tokens with a hyphen.
    - Run through `slugify` to remove any remaining invalid chars.
    """
    if not scope:
        return "meta"
    # split on dot, slash or backslash
    parts = re.split(r"[.\\/]+", scope)
    tokens = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # basic singularization: drop trailing 's' when present
        if p.endswith("s") and len(p) > 1:
            p = p[:-1]
        tokens.append(p)
    joined = "-".join(tokens)
    return slugify(joined)


def parse_udi(udi: str):
    if not udi:
        return None
    parts = udi.split(".")
    if len(parts) != 4:
        return None
    return {"namespace": parts[0], "scope": parts[1], "kind": parts[2], "slug": parts[3]}


def build_udi(namespace: str, scope: str, kind: str, slug: str) -> str:
    return f"{namespace}.{scope}.{kind}.{slug}"


def validate_udi(udi: str):
    errors = []
    if not udi:
        errors.append("empty")
        return False, errors
    if not UDI_REGEX.match(udi):
        errors.append("pattern_mismatch")
    parsed = parse_udi(udi)
    if parsed:
        if parsed["namespace"] not in CANONICAL_NAMESPACES:
            errors.append("invalid_namespace")
        if parsed["kind"] not in CANONICAL_KINDS:
            errors.append("invalid_kind")
        if len(parsed["slug"]) > 64:
            errors.append("slug_too_long")
    else:
        errors.append("segment_count")
    return len(errors) == 0, errors


def derive_udi_from_path_and_content(path: str, metadata_name: str = None, namespace: str = "prismata", scope: str = None, kind: str = None):
    # Minimal deterministic derivation using given hints
    slug = slugify(metadata_name or path.split("/")[-1].split(".")[0])
    if not scope:
        # fallback: use parent folder name
        parts = path.replace("\\", "/").split("/")
        if len(parts) >= 2:
            scope = parts[-2]
        else:
            scope = "meta"
    # normalize scope tokens (handles dots in folder names like 'projects.manifests')
    scope = normalize_scope(scope)

    if not kind:
        kind = "metadata"
    return build_udi(namespace, scope, kind, slug)
