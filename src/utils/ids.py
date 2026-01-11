import hashlib


def stable_id(value: str, prefix: str = "") -> str:
    normalized = value.strip().lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{digest}" if prefix else digest
