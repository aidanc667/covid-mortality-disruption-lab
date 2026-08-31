"""Local raw/processed-data caching with provenance metadata, per brief section 44.

Every cached file is written alongside a `<name>.meta.json` recording the
download timestamp, source URL, and a SHA-256 checksum, so re-running the
pipeline never re-downloads unchanged upstream data and every processed file
can be traced back to exactly what was pulled and when.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_with_provenance(path: Path, content: bytes, source_url: str, source_note: str = "") -> None:
    """Write `content` to `path` and a sibling `.meta.json` with provenance."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    meta = {
        "source_url": source_url,
        "source_note": source_note,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": _checksum(path),
        "bytes": len(content),
    }
    path.with_suffix(path.suffix + ".meta.json").write_text(json.dumps(meta, indent=2))


def is_cached(path: Path) -> bool:
    """A file is considered cached only if both the data file and its provenance
    sidecar exist — a data file without provenance is treated as untrusted."""
    return path.exists() and path.with_suffix(path.suffix + ".meta.json").exists()


def load_meta(path: Path) -> dict:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    return json.loads(meta_path.read_text())
