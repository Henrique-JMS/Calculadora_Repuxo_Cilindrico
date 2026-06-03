"""
precache.py
===========
Pre-compute and cache results for default input values.

Eliminates the computation wait on the very first app load by
shipping pre-computed results that are loaded when all inputs
match the factory defaults.

Usage:
    # Generate the cache file (run after changing calculation logic)
    python precache.py

    # In app.py:
    from precache import load_cache, inputs_are_default
    cache = load_cache()
    if cache is not None and inputs_are_default(current_inputs):
        blank_res, seq_res, proc_res, gif_bytes = cache
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from blank_calculator import compute_blank, BlankResult
from gif_renderer import generate_animation_gif
from pass_sequence import compute_pass_sequence, PassSequenceResult
from process_data import compute_process_data, ProcessDataResult

CACHE_FILENAME = "default_cache.pkl"
CACHE_PATH = Path(__file__).parent / CACHE_FILENAME

DefaultCache = Tuple[BlankResult, PassSequenceResult, ProcessDataResult, bytes]

DEFAULT_INPUTS: Dict[str, Any] = {
    "d_i": 60.0,
    "H": 50.0,
    "d_f": 120.0,
    "t": 1.5,
    "r_die": 6.0,
    "r_punch": 4.5,
    "uts": 310.0,
    "ys": 175.0,
    "m1_lim": 0.50,
    "mn_lim": 0.75,
    "trim_fraction": 0.03,
    "safety_factor": 1.25,
    "mat_choice": "DC01 / DC04 (Aço baixo carbono)",
}


def compute_default_cache() -> DefaultCache:
    """
    Run the full computation pipeline with default inputs and return
    all four result objects.
    """
    d_i = 60.0
    H = 50.0
    d_f = 120.0
    t = 1.5
    r_die = 6.0
    r_punch = 4.5
    uts = 310.0
    ys = 175.0
    m1_lim = 0.50
    mn_lim = 0.75
    trim_fraction = 0.03
    safety_factor = 1.25

    blank_res = compute_blank(
        d_i=d_i, H=H, d_f=d_f, t=t,
        r_punch=r_punch, trim_fraction=trim_fraction,
    )
    seq_res = compute_pass_sequence(
        d_blank=blank_res.d_blank_final,
        d_i=d_i, H=H, t=t,
        r_die_final=r_die, r_punch_final=r_punch,
        m1_lim=m1_lim, mn_lim=mn_lim, d_f=d_f,
    )
    proc_res = compute_process_data(
        passes_geom=seq_res.passes,
        d_blank=blank_res.d_blank_final,
        d_f=d_f, H=H, t=t,
        uts=uts, ys=ys, safety_factor=safety_factor,
    )
    gif_bytes = generate_animation_gif(
        blank_res, seq_res, t=t, d_f=d_f, d_i=d_i,
    )
    return blank_res, seq_res, proc_res, gif_bytes


def save_cache(cache: DefaultCache, path: Path = CACHE_PATH) -> None:
    """Pickle the 4-tuple of results to *path*."""
    with open(path, "wb") as f:
        pickle.dump(cache, f)


def load_cache(path: Path = CACHE_PATH) -> Optional[DefaultCache]:
    """
    Load cached results from *path*.

    Returns None if the file does not exist or cannot be unpickled
    (e.g. because the module layout changed).
    """
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, ModuleNotFoundError, AttributeError, EOFError):
        return None


def inputs_are_default(inputs: Dict[str, Any]) -> bool:
    """
    Return True when every key in *inputs* matches its corresponding
    default value within a small float tolerance.
    """
    TOL = 1e-6
    for key, default_val in DEFAULT_INPUTS.items():
        if key not in inputs:
            return False
        val = inputs[key]
        if isinstance(default_val, float):
            if abs(val - default_val) > TOL:
                return False
        elif val != default_val:
            return False
    return True


if __name__ == "__main__":
    import sys
    print(f"Computing default results ... ", end="", flush=True)
    cache = compute_default_cache()
    save_cache(cache)
    print("OK")
    print(f"Saved to {CACHE_PATH.resolve()}")
    sys.exit(0)
