"""
materials.py
============
Material database for the cylindrical drawing calculator.

Each material entry contains:
    - name          : Display name (str)
    - uts           : Ultimate Tensile Strength — Rm (MPa)
    - ys            : Yield Strength — Re (MPa)
    - m1_lim        : Limiting drawing coefficient for the 1st pass (–)
    - mn_lim        : Limiting drawing coefficient for subsequent passes (–)
    - mu            : Coulomb friction coefficient with lubrication (–)
    - clearance_k   : Punch–die clearance constant k (for c = t + k*sqrt(10t))
    - notes         : Short technical note (str)

All stress values are in MPa. Coefficients are dimensionless.

Usage:
    from materials import get_material, list_material_names, CUSTOM_KEY

    mat = get_material("DC01 / DC04 (Aço baixo carbono)")
    print(mat.uts)   # 310

References:
    - EN 10130 / ASTM A1008 (cold-rolled low-carbon steel)
    - EN 10088 (stainless steel)
    - EN 573 / ASTM B209 (aluminium alloys)
    - Kalpakjian, S. & Schmid, S.R. — Manufacturing Engineering and Technology, 7th ed.
    - Marciniak, Z., Duncan, J.L., Hu, S.J. — Mechanics of Sheet Metal Forming, 2nd ed.
    - Schuler GmbH — Metal Forming Handbook, Springer, 1998.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from constants import (
    DEFAULT_M1_LIM,
    DEFAULT_MN_LIM,
    CLEARANCE_K_STEEL,
    CLEARANCE_K_STAINLESS,
    CLEARANCE_K_ALUMINIUM,
    CLEARANCE_K_COPPER,
)

# Sentinel key for user-defined (custom) material
CUSTOM_KEY: str = "Personalizado (inserir manualmente)"


@dataclass(frozen=True)
class Material:
    """Immutable container for material drawing properties."""

    name: str
    uts: float          # Ultimate Tensile Strength, MPa
    ys: float           # Yield Strength, MPa
    m1_lim: float       # Limiting drawing coefficient — 1st pass
    mn_lim: float       # Limiting drawing coefficient — subsequent passes
    mu: float           # Coulomb friction coefficient (lubricated)
    clearance_k: float  # Punch–die clearance constant k
    notes: str = ""

    # ------------------------------------------------------------------ #
    #  Derived / computed properties                                       #
    # ------------------------------------------------------------------ #

    @property
    def ldr(self) -> float:
        """Limiting Drawing Ratio for the 1st pass (= 1 / m1_lim)."""
        return 1.0 / self.m1_lim

    @property
    def ldr_subsequent(self) -> float:
        """Limiting Drawing Ratio for subsequent passes (= 1 / mn_lim)."""
        return 1.0 / self.mn_lim

    @property
    def bh_pressure(self) -> float:
        """
        Practical blank-holder pressure (MPa).

        Rule: p_bh = 0.015 * Ys  (Kawai empirical formula, industry standard).
        """
        from constants import BH_PRESSURE_COEFF
        return BH_PRESSURE_COEFF * self.ys

    def clearance(self, t: float) -> float:
        """
        Punch–die clearance per side (mm).

        Formula: c = t + k * sqrt(10 * t)
        where k is the material-dependent clearance constant.

        Args:
            t: Sheet thickness (mm).

        Returns:
            Clearance per side (mm).
        """
        import math
        return t + self.clearance_k * math.sqrt(10.0 * t)

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Material database
# ---------------------------------------------------------------------------

_MATERIALS: Dict[str, Material] = {

    "DC01 / DC04 (Aço baixo carbono)": Material(
        name="DC01 / DC04 (Aço baixo carbono)",
        uts=310.0,
        ys=175.0,
        m1_lim=0.50,
        mn_lim=0.75,
        mu=0.12,
        clearance_k=CLEARANCE_K_STEEL,
        notes=(
            "Aço de embutimento profundo, EN 10130. "
            "DC04 tem melhor conformabilidade que DC01. "
            "UTS e Ys representam valores médios da faixa normalizada."
        ),
    ),

    "Aço inoxidável AISI 304": Material(
        name="Aço inoxidável AISI 304",
        uts=600.0,
        ys=255.0,
        m1_lim=0.55,
        mn_lim=0.78,
        mu=0.15,
        clearance_k=CLEARANCE_K_STAINLESS,
        notes=(
            "Austenitic stainless steel; high work-hardening rate requires "
            "larger die radii and generous lubrication. "
            "m1_lim conservativo pela alta resistência ao encruamento."
        ),
    ),

    "Alumínio 1100-O (puro, recozido)": Material(
        name="Alumínio 1100-O (puro, recozido)",
        uts=100.0,
        ys=38.0,
        m1_lim=0.53,
        mn_lim=0.76,
        mu=0.10,
        clearance_k=CLEARANCE_K_ALUMINIUM,
        notes=(
            "Alumínio comercialmente puro, estado recozido (O). "
            "Excelente conformabilidade. Sensível a rugas devido ao baixo Ys. "
            "Requer controle cuidadoso da pressão do prensa-chapas."
        ),
    ),

    "Alumínio 3003-H14": Material(
        name="Alumínio 3003-H14",
        uts=165.0,
        ys=140.0,
        m1_lim=0.52,
        mn_lim=0.75,
        mu=0.10,
        clearance_k=CLEARANCE_K_ALUMINIUM,
        notes=(
            "Liga Al-Mn, estado H14 (semi-encruado). "
            "Boa relação resistência/conformabilidade. "
            "Largamente usado em embalagens e utensílios."
        ),
    ),

    "Cobre ETP C11000 (recozido)": Material(
        name="Cobre ETP C11000 (recozido)",
        uts=240.0,
        ys=85.0,
        m1_lim=0.50,
        mn_lim=0.73,
        mu=0.10,
        clearance_k=CLEARANCE_K_COPPER,
        notes=(
            "Cobre eletrolítico de alta pureza, estado recozido. "
            "Alta ductilidade; muito bom LDR. "
            "Pode requerer recozimento intermediário em produtos profundos."
        ),
    ),

    "Latão 70/30 (CuZn30, recozido)": Material(
        name="Latão 70/30 (CuZn30, recozido)",
        uts=350.0,
        ys=140.0,
        m1_lim=0.52,
        mn_lim=0.75,
        mu=0.12,
        clearance_k=CLEARANCE_K_COPPER,
        notes=(
            "Liga Cu-Zn 70/30, estado recozido. "
            "Clássico material de embutimento; excelente acabamento superficial. "
            "Susceptível à corrosão por tensão — evitar água com amônia."
        ),
    ),

    CUSTOM_KEY: Material(
        name=CUSTOM_KEY,
        uts=0.0,
        ys=0.0,
        m1_lim=DEFAULT_M1_LIM,
        mn_lim=DEFAULT_MN_LIM,
        mu=0.12,
        clearance_k=CLEARANCE_K_STEEL,
        notes="Material definido pelo usuário. Preencha UTS e Ys manualmente.",
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_material_names() -> List[str]:
    """
    Return the ordered list of material display names.

    The custom entry is always placed last.

    Returns:
        List of material name strings.
    """
    standard = [k for k in _MATERIALS if k != CUSTOM_KEY]
    return standard + [CUSTOM_KEY]


def get_material(name: str) -> Material:
    """
    Retrieve a Material object by its display name.

    Args:
        name: Material name exactly as returned by list_material_names().

    Returns:
        The corresponding Material instance.

    Raises:
        KeyError: If the name is not found in the database.
    """
    if name not in _MATERIALS:
        available = ", ".join(_MATERIALS.keys())
        raise KeyError(
            f"Material '{name}' not found. "
            f"Available options: {available}"
        )
    return _MATERIALS[name]


def build_custom_material(
    uts: float,
    ys: float,
    m1_lim: float = DEFAULT_M1_LIM,
    mn_lim: float = DEFAULT_MN_LIM,
    mu: float = 0.12,
    clearance_k: float = CLEARANCE_K_STEEL,
) -> Material:
    """
    Build a custom Material instance from user-provided values.

    Args:
        uts:        Ultimate Tensile Strength (MPa). Must be > 0.
        ys:         Yield Strength (MPa). Must be > 0 and <= uts.
        m1_lim:     Drawing coefficient limit — 1st pass (0.40–0.65).
        mn_lim:     Drawing coefficient limit — subsequent passes (0.60–0.90).
        mu:         Friction coefficient (0.05–0.30).
        clearance_k: Punch–die clearance constant (default: steel).

    Returns:
        A Material instance with name == CUSTOM_KEY.

    Raises:
        ValueError: If any parameter is out of a physically meaningful range.
    """
    if uts <= 0:
        raise ValueError(f"UTS must be > 0 MPa. Got {uts}.")
    if ys <= 0:
        raise ValueError(f"Yield Strength must be > 0 MPa. Got {ys}.")
    if ys > uts:
        raise ValueError(
            f"Yield Strength ({ys} MPa) cannot exceed UTS ({uts} MPa)."
        )
    if not (0.35 <= m1_lim <= 0.70):
        raise ValueError(
            f"m1_lim must be between 0.35 and 0.70. Got {m1_lim}."
        )
    if not (0.55 <= mn_lim <= 0.95):
        raise ValueError(
            f"mn_lim must be between 0.55 and 0.95. Got {mn_lim}."
        )
    if mn_lim <= m1_lim:
        raise ValueError(
            f"mn_lim ({mn_lim}) must be greater than m1_lim ({m1_lim}). "
            "Subsequent passes are always less severe than the first."
        )
    if not (0.05 <= mu <= 0.30):
        raise ValueError(
            f"Friction coefficient mu must be between 0.05 and 0.30. Got {mu}."
        )

    return Material(
        name=CUSTOM_KEY,
        uts=uts,
        ys=ys,
        m1_lim=m1_lim,
        mn_lim=mn_lim,
        mu=mu,
        clearance_k=clearance_k,
        notes="User-defined custom material.",
    )
