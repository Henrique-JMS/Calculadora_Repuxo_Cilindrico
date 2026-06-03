"""
tests/test_precache.py
=======================
Verify that the pre-computed cache matches fresh computation.

If the calculation logic in blank_calculator, pass_sequence or
process_data changes, the cache becomes stale.  This test detects
that by re-computing with default inputs and comparing every
numerical field against the cached values.

A clear diff is printed so the developer knows to re-run:
    python precache.py
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import fields, is_dataclass
from typing import Any, Dict, List, Tuple

import pytest

from precache import (
    compute_default_cache,
    load_cache,
    CACHE_PATH,
)


pytestmark = pytest.mark.skipif(
    not CACHE_PATH.exists(),
    reason=f"Pre-cache file not found at {CACHE_PATH} — run 'python precache.py' first",
)


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

class NumericalMismatchError(AssertionError):
    """Raised when a numerical field differs between cached and fresh data."""

    def __init__(self, path: str, cached: Any, fresh: Any) -> None:
        self.path = path
        self.cached = cached
        self.fresh = fresh
        super().__init__(self._format())

    def _format(self) -> str:
        return (
            f"\n  {'─' * 60}"
            f"\n  Mismatch at  {self.path}"
            f"\n    cached:   {self.cached!r}"
            f"\n    fresh:    {self.fresh!r}"
            f"\n    diff:     {self._diff()}"
            f"\n  {'─' * 60}"
        )

    def _diff(self) -> str:
        if isinstance(self.cached, float) and isinstance(self.fresh, float):
            return f"{self.fresh - self.cached:+.6e}"
        return "—"


def _check(path: str, cached: Any, fresh: Any) -> None:
    """Recursively compare two values, collecting errors."""

    if isinstance(cached, float) and isinstance(fresh, float):
        if abs(cached - fresh) > 1e-6:
            raise NumericalMismatchError(path, cached, fresh)
        return

    if isinstance(cached, int) and isinstance(fresh, int):
        if cached != fresh:
            raise NumericalMismatchError(path, cached, fresh)
        return

    if isinstance(cached, str) and isinstance(fresh, str):
        if cached != fresh:
            raise NumericalMismatchError(path, cached, fresh)
        return

    if isinstance(cached, bool) and isinstance(fresh, bool):
        if cached != fresh:
            raise NumericalMismatchError(path, cached, fresh)
        return

    if cached is None and fresh is None:
        return

    if isinstance(cached, (list, tuple)) and isinstance(fresh, (list, tuple)):
        if len(cached) != len(fresh):
            raise NumericalMismatchError(
                f"{path} (length)", len(cached), len(fresh)
            )
        for i, (c, f) in enumerate(zip(cached, fresh)):
            _check(f"{path}[{i}]", c, f)
        return

    if is_dataclass(cached) and is_dataclass(fresh):
        for field in fields(cached):
            _check(f"{path}.{field.name}",
                   getattr(cached, field.name),
                   getattr(fresh, field.name))
        return

    # bytes: skip comparison (platform-dependent rendering)
    if isinstance(cached, bytes) and isinstance(fresh, bytes):
        return

    raise TypeError(
        f"Cannot compare {type(cached).__name__} vs {type(fresh).__name__} "
        f"at {path}"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPrecacheSync:

    def test_cache_file_exists(self) -> None:
        """Sanity check — the skip marker already ensures this."""
        assert CACHE_PATH.exists(), (
            f"Pre-cache file not found. Run 'python precache.py'"
        )

    def test_precache_matches_fresh_computation(self) -> None:
        """
        Core test: load cached data, re-compute, compare all fields.

        Every float, int, str and bool field in the four result objects
        is compared.  Any mismatch triggers a detailed diff showing
        the exact path, values and numeric difference.
        """
        cached = load_cache()
        assert cached is not None, "Failed to load cache file"

        fresh = compute_default_cache()

        names = ("blank_res", "seq_res", "proc_res", "gif_bytes")

        errors: List[str] = []
        for name, c_val, f_val in zip(names, cached, fresh):
            try:
                _check(name, c_val, f_val)
            except NumericalMismatchError as exc:
                errors.append(str(exc))

        if errors:
            msg = (
                f"\n{'=' * 60}"
                f"\n  Pre-cache is STALE — {len(errors)} mismatch(es) found."
                f"\n  Re-run:  python precache.py"
                f"\n{'=' * 60}"
            )
            for err in errors:
                msg += err
            pytest.fail(msg)

    def test_cache_gif_is_nonempty(self) -> None:
        """GIF bytes should be present and non-empty."""
        cached = load_cache()
        assert cached is not None
        gif_bytes = cached[3]
        assert isinstance(gif_bytes, bytes), "GIF is not bytes"
        assert len(gif_bytes) > 100, f"GIF too small: {len(gif_bytes)} bytes"

    def test_cache_gif_is_valid_png_or_gif(self) -> None:
        """The cached bytes should start with a valid GIF header."""
        cached = load_cache()
        assert cached is not None
        gif_bytes = cached[3]
        # GIF header: 'GIF87a' or 'GIF89a'
        assert gif_bytes[:3] == b"GIF", (
            f"Expected GIF header, got {gif_bytes[:6]!r}"
        )
