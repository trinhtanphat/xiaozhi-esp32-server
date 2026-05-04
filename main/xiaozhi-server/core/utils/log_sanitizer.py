def redact_transcript_for_log(text, placeholder="[TRANSCRIPT_REDACTED]") -> str:
    """Return a safe placeholder for user/assistant transcript log messages."""
    if text is None:
        return f"{placeholder}(len=0)"
    try:
        length = len(text)
    except TypeError:
        length = 0
    return f"{placeholder}(len={length})"
