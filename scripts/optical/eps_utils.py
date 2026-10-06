#!/usr/bin/env python3
"""Shared epsr/epsi (real/imaginary dielectric function) parsing and per-axis optical-magnitude
formulas, used by both the Dielectric function plotter and the Optical-magnitudes plotter.

File parsing is the same generalized reader validated in `scripts/tauc/absorption_from_eps.py`
(skip '#' comment lines, drop a leading E=0 row) -- duplicated here rather than imported so this
module has no dependency on the Tauc module, since the two are independent candidate pages.

Formulas below are unchanged from the user's validated one-off pipeline
(`All-Scripts/0-Updated-V2-Scripts-Optical-Properties-Calculation/16E..21E-*.py`), generalized
to operate on any axis (not hardcoded to X/Y/Z column positions) so the same code serves the
"Ordinary" (a-axis) and "Extraordinary" (c-axis) polarization choice for any wurtzite material,
or any other axis convention a future non-wurtzite material might need.

All formulas take e1 (epsr) and e2 (epsi) at one energy point and return one derived value:
    n       = refractive index       = (1/sqrt2) * sqrt( sqrt(e1^2+e2^2) + e1 )
    k       = extinction coefficient = (1/sqrt2) * sqrt( sqrt(e1^2+e2^2) - e1 )
    R       = reflectivity           = ((1-n)^2 + k^2) / ((1+n)^2 + k^2)
    alpha   = absorption coeff.      = (4*pi/wavelength_nm) * k * 1e7 * 1e-4   [1e4/cm]
    eels    = energy-loss function   = e2 / (e1^2 + e2^2)
    sigma   = optical conductivity   = eps0 * omega * e2 * 1e-4, omega = 2*pi*c/wavelength_nm
"""

import math

# Default wavelength-axis window (nm): the visible-ish UV-Vis-NIR range that's actually
# readable, since epsilon.x's own energy grid spans deep-UV to far-IR and a full auto-range in
# wavelength would be dominated by a long, uninformative tail. Still overridable via x_range.
DEFAULT_WAVELENGTH_RANGE_NM = (100.0, 1000.0)

H_PLANCK = 6.62607015e-34
C_LIGHT = 299792458
E_CHARGE = 1.60217663e-19
EPS0 = 8.8541878188e-12


def load_eps_file(path):
    """Return list of (energy_eV, x, y, z) tuples from an epsilon.x-style file."""
    rows = []
    with open(path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) < 4:
                continue
            rows.append(tuple(float(p) for p in parts[:4]))

    if not rows:
        raise ValueError(f"No numeric data rows found in {path}")

    if abs(rows[0][0]) < 1e-9:
        rows = rows[1:]

    if not rows:
        raise ValueError(f"{path} only contained a single (E=0) data row after filtering")

    return rows


def energy_to_wavelength_nm(energy_ev):
    return (H_PLANCK * C_LIGHT) / (energy_ev * E_CHARGE * 1e-9)


def refractive_index(e1, e2):
    return (1 / math.sqrt(2)) * math.sqrt(max(math.sqrt(e1 ** 2 + e2 ** 2) + e1, 0.0))


def extinction_coefficient(e1, e2):
    return (1 / math.sqrt(2)) * math.sqrt(max(math.sqrt(e1 ** 2 + e2 ** 2) - e1, 0.0))


def reflectivity(e1, e2):
    n = refractive_index(e1, e2)
    k = extinction_coefficient(e1, e2)
    return ((1 - n) ** 2 + k ** 2) / ((1 + n) ** 2 + k ** 2)


def absorption_coefficient(e1, e2, energy_ev):
    wavelength_nm = energy_to_wavelength_nm(energy_ev)
    k = extinction_coefficient(e1, e2)
    return (4 * math.pi / wavelength_nm) * k * 1e7 * 1e-4


def energy_loss_function(e1, e2):
    denom = e1 ** 2 + e2 ** 2
    return e2 / denom if denom else 0.0


def optical_conductivity(e1, e2, energy_ev):
    wavelength_nm = energy_to_wavelength_nm(energy_ev)
    omega = (2 * math.pi * C_LIGHT) / (wavelength_nm * 1e-9)
    return EPS0 * omega * e2 * 1e-4


MAGNITUDE_FUNCS = {
    'Refractive index': lambda e1, e2, e: refractive_index(e1, e2),
    'Extinction coefficient': lambda e1, e2, e: extinction_coefficient(e1, e2),
    'Reflectivity': lambda e1, e2, e: reflectivity(e1, e2),
    'Absorption coefficient': lambda e1, e2, e: absorption_coefficient(e1, e2, e),
    'Energy-loss function': lambda e1, e2, e: energy_loss_function(e1, e2),
    'Optical conductivity': lambda e1, e2, e: optical_conductivity(e1, e2, e),
}

MAGNITUDE_YLABEL = {
    'Refractive index': 'n',
    'Extinction coefficient': 'k',
    'Reflectivity': 'R',
    'Absorption coefficient': r'$\alpha$ ($10^4$ cm$^{-1}$)',
    'Energy-loss function': 'L(ω)',
    'Optical conductivity': r'$\sigma$ (S/cm)',
}

AXIS_INDEX = {'Ordinary': 1, 'Extraordinary': 3}  # 1=X (a-axis), 3=Z (c-axis) in epsilon.x column order
