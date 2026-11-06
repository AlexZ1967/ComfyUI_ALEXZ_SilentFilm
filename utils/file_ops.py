"""Publish completed local files without overwriting existing destinations."""

import os
from pathlib import Path
import sys


def publish_file(source, target):
    """Publish a same-directory temporary file with native no-clobber semantics."""
    if sys.platform == "win32":
        # На Windows rename атомарен и отказывает, если имя уже занято;
        # в отличие от hard link он работает и на файловых системах без ссылок.
        os.rename(source, target)
    else:
        # POSIX rename может перезаписать файл, поэтому сохраняем hard link.
        os.link(source, target)


def validate_upload_filename(name, suffixes):
    """Accept a single video filename that is also safe on Windows filesystems."""
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789¹²³")
    device = name.split(".", 1)[0].rstrip(" ").upper()
    if (not name or name.startswith(".") or name.endswith((" ", "."))
            or any(c in name for c in '/\\:<>"|?*') or any(ord(c) < 32 for c in name)
            or len(name.encode("utf-8")) > 240 or device in reserved
            or Path(name).suffix.lower() not in suffixes):
        raise ValueError("Некорректное имя видеофайла; используйте имя без зарезервированных Windows-символов и имён устройств.")
    return name
