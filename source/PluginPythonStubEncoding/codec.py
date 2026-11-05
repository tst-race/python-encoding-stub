"""Replace these hooks with calls to the selected Python encoding library."""


def encode(payload: bytes, parameters: str) -> bytes:
    """Return encoded content for payload and EncodingParameters.json."""
    raise NotImplementedError("Implement encode using the selected Python library")


def decode(content: bytes, parameters: str) -> bytes:
    """Recover the exact original payload or raise on invalid content."""
    raise NotImplementedError("Implement decode using the selected Python library")