import logging


class SingleLineNonEmptyFilter(logging.Filter):
    """
    Logging filter that ensures messages are single-line and non-empty.
    - Collapses newlines into spaces and strips surrounding whitespace.
    - Drops the record if the resulting message is empty.
    """
    def filter(self, record: logging.LogRecord) -> int:
        try:
            msg = record.getMessage()
        except Exception:
            # If formatting fails, drop the record
            return 0

        # Convert any non-string to string representation
        if not isinstance(msg, str):
            msg = str(msg)

        # Collapse multi-line to single line and trim
        sanitized = " ".join(msg.splitlines()).strip()

        if sanitized == "":
            return 0

        # If we changed the message, update the record and clear args
        if sanitized != record.getMessage():
            record.msg = sanitized
            record.args = ()
        return 1