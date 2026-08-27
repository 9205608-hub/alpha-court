"""Data pack presence / optional download (killer-demo.md §9.1).

Pinned tag ``2026-07-05`` (chenditc/investment_data). Download is idempotent:
presence of calendars/day.txt plus measured calendar end fingerprint.
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from examples.killer_demo.config import (
    DATA_DOWNLOAD_URL,
    DECLARED_DATA_TAG,
    PROVISIONAL_WINDOW_END,
)


def calendar_end_iso(provider_uri: str | Path) -> str:
    """Last calendar day in the pack (ISO)."""
    path = Path(provider_uri) / "calendars" / "day.txt"
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"empty calendar: {path}")
    return lines[-1]


def data_pack_ready(
    provider_uri: str | Path,
    *,
    expected_calendar_end: str = PROVISIONAL_WINDOW_END,
) -> bool:
    """True if pack exists and calendar end matches the pinned fingerprint."""
    root = Path(provider_uri)
    cal = root / "calendars" / "day.txt"
    if not cal.is_file():
        return False
    features = root / "features"
    if not features.is_dir():
        return False
    try:
        end = calendar_end_iso(root)
    except (OSError, ValueError):
        return False
    return end == expected_calendar_end


def ensure_data_pack(
    provider_uri: str | Path,
    *,
    skip_download: bool = False,
    url: str = DATA_DOWNLOAD_URL,
    expected_calendar_end: str = PROVISIONAL_WINDOW_END,
) -> Path:
    """Ensure the pinned data pack is present; optionally download (§9.1)."""
    root = Path(provider_uri).expanduser()
    if data_pack_ready(root, expected_calendar_end=expected_calendar_end):
        return root

    if skip_download:
        raise FileNotFoundError(
            f"data pack not ready at {root} (skip_download=True). "
            f"Expected calendars/day.txt ending at {expected_calendar_end} "
            f"(declared tag {DECLARED_DATA_TAG})."
        )

    root.mkdir(parents=True, exist_ok=True)
    tarball = root.parent / f"qlib_bin_{DECLARED_DATA_TAG}.tar.gz"
    print(f"[data] downloading {url} → {tarball}", flush=True)
    urllib.request.urlretrieve(url, tarball)  # noqa: S310 — pinned release URL
    print(f"[data] extracting into {root}", flush=True)
    with tarfile.open(tarball, "r:gz") as tf:
        tf.extractall(path=root)
    if not data_pack_ready(root, expected_calendar_end=expected_calendar_end):
        raise RuntimeError(
            f"download completed but pack fingerprint failed at {root}; "
            f"expected calendar end {expected_calendar_end}"
        )
    return root
