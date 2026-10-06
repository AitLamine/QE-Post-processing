#!/usr/bin/env python3
"""Merge X/Y/Z absorption-coefficient files into one energy-sorted and one wavelength-sorted
file.

Direct port of the user's validated `All-Scripts/1-Absorption-Coefficient-Data-Processor.py`
(logic unchanged; only the CLI was switched to argparse and file objects to numpy operations
were left as-is). Input files: 2 columns each (Energy(eV), Alpha[x10^4/cm]), as produced by
`absorption_from_eps.py`.
"""

import argparse
import sys

import numpy as np


def read_absorption_file(filename):
    """Read absorption data from file (energy, alpha)."""
    data = np.loadtxt(filename)
    energy = data[:, 0]  # in eV
    alpha = data[:, 1]  # in 10^4/cm
    return energy, alpha


def energy_to_wavelength(energy_eV):
    """Convert energy (eV) to wavelength (nm). lambda(nm) = hc/E = 1239.84193 / E(eV)."""
    return 1239.84193 / energy_eV


def merge(file_x, file_y, file_z, output_energy, output_wavelength):
    energy_x, alpha_x = read_absorption_file(file_x)
    energy_y, alpha_y = read_absorption_file(file_y)
    energy_z, alpha_z = read_absorption_file(file_z)

    if not (np.allclose(energy_x, energy_y) and np.allclose(energy_x, energy_z)):
        print("Warning: Energy points differ between files. Using first file's energies.")

    energy = energy_x
    wavelength = energy_to_wavelength(energy)

    print(f"Writing energy-sorted data to {output_energy}...")
    with open(output_energy, 'w') as f:
        f.write("# Energy(eV)   Wavelength(nm)  Alpha1(x10^4/cm)  Alpha2(x10^4/cm)  Alpha3(x10^4/cm)\n")
        for i in range(len(energy)):
            f.write(f"{energy[i]:12.9f}   {wavelength[i]:10.4f}   "
                    f"{alpha_x[i]:13.9f}   {alpha_y[i]:13.9f}   {alpha_z[i]:13.9f}\n")

    sort_indices = np.argsort(wavelength)
    energy_sorted = energy[sort_indices]
    wavelength_sorted = wavelength[sort_indices]
    alpha_x_sorted = alpha_x[sort_indices]
    alpha_y_sorted = alpha_y[sort_indices]
    alpha_z_sorted = alpha_z[sort_indices]

    print(f"Writing wavelength-sorted data to {output_wavelength}...")
    with open(output_wavelength, 'w') as f:
        f.write("# Wavelength(nm)  Energy(eV)   Alpha1(x10^4/cm)  Alpha2(x10^4/cm)  Alpha3(x10^4/cm)\n")
        for i in range(len(wavelength_sorted)):
            f.write(f"{wavelength_sorted[i]:10.4f}  {energy_sorted[i]:12.9f}  "
                    f"{alpha_x_sorted[i]:15.8f}  {alpha_y_sorted[i]:15.8f}  {alpha_z_sorted[i]:15.8f}\n")

    print("Processing complete!")
    print(f"  Energy range: {energy[0]:.6f} - {energy[-1]:.6f} eV")
    print(f"  Wavelength range: {wavelength_sorted[0]:.4f} - {wavelength_sorted[-1]:.4f} nm")
    print(f"  Number of data points: {len(energy)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file_x')
    parser.add_argument('file_y')
    parser.add_argument('file_z')
    parser.add_argument('output_energy')
    parser.add_argument('output_wavelength')
    args = parser.parse_args()

    try:
        merge(args.file_x, args.file_y, args.file_z, args.output_energy, args.output_wavelength)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
