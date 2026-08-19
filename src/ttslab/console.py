from __future__ import annotations

import sys
from typing import TextIO


def configure_utf8_stdio() -> None:
    """Keep product/research CLI output Unicode-safe on legacy Windows console encodings.

    Python can inherit cp1252 from a Windows process even when PowerShell itself is Unicode-aware.
    That becomes visible when JSON contains a path, voice name, transcript, or metadata in Arabic,
    Cyrillic, CJK, etc. Reconfigure text streams to UTF-8 when the runtime exposes that operation.
    The helper is deliberately best-effort so embedded/test streams without `reconfigure` keep
    working normally.
    """
    for stream in (sys.stdout, sys.stderr):
        _configure_stream(stream)


def _configure_stream(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, OSError, ValueError):
        # A replaced/captured stream may reject reconfiguration. The caller should still run.
        return
