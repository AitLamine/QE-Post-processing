"""
Parses a *_scipy_fitting_results.txt file and computes the effective mass
m*/m0 = hbar^2 (2*pi/a)^2 / |d2E/dk2|, writing the final _plot_data.txt (k,
original E, fitted E) and _info.txt (full derivation) files.

Ported from the validated one-off toolkit
(Effective-Mass-Calculation-Plot-Data-Generation.py). The only change:
write_info_file() now branches on lattice["manual_entry"] (set by
Manual-Configuration.py) so the "Lattice constant, auto-extracted" provenance
block - which assumes celldm(1)/celldm(3) and a QE source file exist -
degrades gracefully to a "manually entered" block instead of crashing on the
Nones that Manual-Configuration.py legitimately puts in those fields.
"""

import sys
import os
import math
import json

# ============================================
# CONSTANTS
# ============================================
H_BAR = 6.62607015e-34 / (2 * math.pi)  # Reduced Planck constant (J.s)
H_BAR_SQUARED = H_BAR ** 2  # (J.s)^2
FREE_E_MASS = 9.1093837139e-31  # Free electron mass (kg)
EV_TO_JOULE = 1.602176565e-19  # eV to Joules conversion
BOHR_TO_ANGSTROM = 0.529177210903  # Bohr radius, used to convert celldm(1)/(3) to Angstrom

def load_lattice_info():
    """
    Load the lattice constant resolved by Detect-Configuration.py (auto mode,
    parsed from QE files) or Manual-Configuration.py (manual mode, typed by
    the student), already resolved to whichever axis (a or c) matches this
    direction's k-path in auto mode.
    """
    if not os.path.exists("material_config.json"):
        print("ERROR: material_config.json not found. Run Detect-Configuration.py "
              "or Manual-Configuration.py first.")
        sys.exit(1)
    with open("material_config.json") as f:
        config = json.load(f)
    return config["lattice"]

def parse_fitting_results(filename):
    """
    Parse the scipy fitting results file and extract relevant information
    """
    data = {
        'a': None,
        'a_err': None,
        'b': None,
        'b_err': None,
        'c': None,
        'c_err': None,
        'second_derivative': None,
        'k_extremum': None,
        'E_extremum': None,
        'extremum_type': None,
        'r_squared': None,
        'rmse': None,
        'plot_data': []
    }

    with open(filename, 'r') as f:
        lines = f.readlines()

    in_data_section = False

    for i, line in enumerate(lines):
        line = line.strip()

        # Extract polynomial coefficients
        if line.startswith('a (k² coefficient):'):
            parts = line.split()
            data['a'] = float(parts[3])
            data['a_err'] = float(parts[5])

        elif line.startswith('b (k coefficient):'):
            parts = line.split()
            data['b'] = float(parts[3])
            data['b_err'] = float(parts[5])

        elif line.startswith('c (constant):'):
            parts = line.split()
            data['c'] = float(parts[2])
            data['c_err'] = float(parts[4])

        # Extract second derivative
        elif line.startswith('∂²E/∂k²'):
            parts = line.split('=')[1].split('±')
            data['second_derivative'] = float(parts[0].strip())

        # Extract extremum information
        elif line.startswith('Type:'):
            data['extremum_type'] = line.split(':')[1].strip()

        elif line.startswith('k-position:'):
            parts = line.split()
            data['k_extremum'] = float(parts[1])

        elif line.startswith('Energy:') and data['E_extremum'] is None:
            parts = line.split()
            data['E_extremum'] = float(parts[1])

        # Extract fit quality
        elif line.startswith('R² (coefficient of determination):'):
            parts = line.split(':')
            data['r_squared'] = float(parts[1].strip())

        elif line.startswith('Root Mean Square Error (RMSE):'):
            parts = line.split(':')
            data['rmse'] = float(parts[1].strip())

        # Extract data table
        elif line.startswith('k-value') and 'Original E' in line:
            in_data_section = True
            continue

        elif in_data_section and line.startswith('-'):
            continue

        elif in_data_section and line:
            try:
                parts = line.split()
                if len(parts) >= 3:
                    k_val = float(parts[0])
                    orig_E = float(parts[1])
                    fitted_E = float(parts[2])
                    data['plot_data'].append([k_val, orig_E, fitted_E])
            except:
                pass

    return data

def calculate_effective_mass(DS, a_lattice):
    """
    Calculate effective mass in units of free electron mass (m₀)

    Parameters:
    -----------
    DS : float
        Second derivative coefficient (a from the quadratic fit)
    a_lattice : float
        Lattice parameter in Angstrom (already resolved to the axis matching
        this direction's k-path, see Detect-Configuration.py, or typed
        directly by the student in manual mode)

    Returns:
    --------
    m_eff : float
        Effective mass in units of m₀
    """
    # Convert second derivative to Joules
    d2E_dk2_joules = DS * 2 * EV_TO_JOULE

    # Calculate h_bar^2 / m0
    h_bar_sq_over_m0 = H_BAR_SQUARED / FREE_E_MASS

    # Convert lattice parameter to meters
    a_lattice_m = a_lattice * 1e-10

    # Calculate (2π/a)²
    two_pi_over_a = 2 * math.pi / a_lattice_m
    two_pi_over_a_squared = two_pi_over_a ** 2

    # Calculate effective mass
    m_eff = (h_bar_sq_over_m0 * two_pi_over_a_squared) / d2E_dk2_joules

    return m_eff

def write_plot_data(filename, plot_data):
    """
    Write plot data to file (k-value, Original_E, Fitted_E)
    """
    with open(filename, 'w') as f:
        f.write("k-value Original_E Fitted_E\n")
        for row in plot_data:
            f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}\n")

def write_info_file(filename, data, m_eff, lattice):
    """
    Write information file with equation and effective mass
    """
    a_lattice = lattice["lattice_constant_angstrom"]
    axis_used = lattice["lattice_axis_used"]
    is_manual = bool(lattice.get("manual_entry"))

    with open(filename, 'w') as f:
        f.write("="*70 + "\n")
        f.write("EXTRACTED FITTING INFORMATION AND EFFECTIVE MASS\n")
        f.write("="*70 + "\n\n")

        # Fitted equation
        f.write("FITTED QUADRATIC EQUATION:\n")
        f.write(f"E(k) = ({data['a']:.8f} ± {data['a_err']:.8f})k² + ")
        f.write(f"({data['b']:.8f} ± {data['b_err']:.8f})k + ")
        f.write(f"({data['c']:.8f} ± {data['c_err']:.8f})\n\n")

        # Coefficients
        f.write("POLYNOMIAL COEFFICIENTS:\n")
        f.write(f"a (k² coefficient): {data['a']:.8f} ± {data['a_err']:.8f}\n")
        f.write(f"b (k coefficient):  {data['b']:.8f} ± {data['b_err']:.8f}\n")
        f.write(f"c (constant):       {data['c']:.8f} ± {data['c_err']:.8f}\n\n")

        # Second derivative
        f.write("SECOND DERIVATIVE:\n")
        f.write(f"∂²E/∂k² = {data['second_derivative']:.8f} eV·Å²\n")
        f.write(f"Note: DS = a = {data['a']:.8f}\n\n")

        # Extremum
        f.write("EXTREMUM INFORMATION:\n")
        f.write(f"Type: {data['extremum_type']}\n")
        f.write(f"k-position: {data['k_extremum']:.8f} Å⁻¹\n")
        f.write(f"Energy: {data['E_extremum']:.8f} eV\n\n")

        # Fit quality
        f.write("FIT QUALITY:\n")
        f.write(f"R²: {data['r_squared']:.8f}\n")
        f.write(f"RMSE: {data['rmse']:.8f} eV\n\n")

        # Effective mass calculation
        f.write("="*70 + "\n")
        f.write("EFFECTIVE MASS CALCULATION\n")
        f.write("="*70 + "\n\n")

        if is_manual:
            f.write("Lattice constant, MANUALLY ENTERED by the student (not parsed from a\n")
            f.write("QE file - use Auto mode for a QE-derived value with full provenance):\n")
            f.write(f"  a = {a_lattice:.6f} Ang = {a_lattice*1e-10:.4e} m\n")
            f.write("  K-path axis for this direction: not applicable (manual mode)\n\n")
        else:
            f.write("Lattice constant, auto-extracted (not hardcoded):\n")
            f.write(f"  Source file          : {lattice['source_file']}\n")
            f.write(f"  celldm(1) (Bohr)     : {lattice['celldm1_bohr']:.8f}\n")
            if lattice.get("celldm3_ratio") is not None:
                f.write(f"  celldm(3) (c/a ratio): {lattice['celldm3_ratio']:.8f}\n")
            f.write(f"  Bohr -> Angstrom factor used: {BOHR_TO_ANGSTROM}\n")
            f.write(f"  a = {lattice['a_angstrom']:.6f} Ang")
            if lattice.get("c_angstrom") is not None:
                f.write(f"   c = {lattice['c_angstrom']:.6f} Ang")
            f.write("\n")
            axis_note = "in-plane a-axis" if axis_used == "a" else "c-axis (Gamma-A k-path)"
            f.write(f"  K-path axis for this direction: {axis_used} ({axis_note})\n")
            f.write(f"  -> lattice constant used: {a_lattice:.6f} Ang = {a_lattice*1e-10:.4e} m\n\n")

        f.write("Parameters used:\n")
        f.write(f"DS (second derivative coefficient): {data['a']:.8f}\n")
        f.write(f"ℏ = {H_BAR:.6e} J·s\n")
        f.write(f"m₀ = {FREE_E_MASS:.10e} kg\n\n")

        f.write("Calculation steps:\n")
        d2E_dk2_joules = data['a'] * 2 * EV_TO_JOULE
        f.write(f"1. |∂²E/∂k²| (J) = DS × 2 × 1.602176565×10⁻¹⁹ = {d2E_dk2_joules:.6e} J\n")

        h_bar_sq_over_m0 = H_BAR_SQUARED / FREE_E_MASS
        f.write(f"2. ℏ²/m₀ = {h_bar_sq_over_m0:.6e} J·m²\n")

        two_pi_over_a_squared = (2 * math.pi / (a_lattice * 1e-10)) ** 2
        f.write(f"3. (2π/a)² = {two_pi_over_a_squared:.6e} m⁻²\n\n")

        f.write(f"EFFECTIVE MASS: m*/m₀ = {m_eff:.6f}\n")
        f.write(f"                m* = {m_eff:.6f} × {FREE_E_MASS:.6e} kg\n")
        f.write(f"                m* = {m_eff * FREE_E_MASS:.6e} kg\n")

def print_summary(data, m_eff, lattice, output_plot, output_info):
    """
    Print summary to terminal
    """
    print("\n" + "="*70)
    print("SUMMARY OF EXTRACTED INFORMATION")
    print("="*70)

    print(f"\nFITTED EQUATION:")
    print(f"E(k) = ({data['a']:.6f} ± {data['a_err']:.6f})k² + ", end="")
    print(f"({data['b']:.6f} ± {data['b_err']:.6f})k + ", end="")
    print(f"({data['c']:.6f} ± {data['c_err']:.6f})")

    print(f"\nEXTREMUM:")
    print(f"Type: {data['extremum_type']}")
    print(f"Position: k = {data['k_extremum']:.6f} Å⁻¹")
    print(f"Energy: E = {data['E_extremum']:.6f} eV")

    print(f"\nFIT QUALITY:")
    print(f"R² = {data['r_squared']:.6f}")
    print(f"RMSE = {data['rmse']:.6f} eV")

    print(f"\nEFFECTIVE MASS:")
    print(f"Lattice axis used  : {lattice['lattice_axis_used']}")
    if lattice.get("manual_entry"):
        print(f"Lattice constant   : {lattice['lattice_constant_angstrom']:.6f} Å (manually entered)")
    else:
        print(f"Lattice constant   : {lattice['lattice_constant_angstrom']:.6f} Å "
              f"(from {lattice['source_file']}, celldm in Bohr converted with {BOHR_TO_ANGSTROM})")
    print(f"m*/m₀ = {m_eff:.6f}")

    print(f"\nOUTPUT FILES:")
    print(f"✓ Plot data saved to: {output_plot}")
    print(f"✓ Information saved to: {output_info}")
    print(f"✓ Total data points: {len(data['plot_data'])}")
    print("="*70 + "\n")

def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <fitting_results_file>")
        print("Example: python3 script.py Bottom-Conduction-Band_scipy_fitting_results.txt")
        sys.exit(1)

    input_filename = sys.argv[1]

    # Check if input file exists
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found!")
        sys.exit(1)

    # Generate output filenames
    base_name = input_filename.replace('_scipy_fitting_results.txt', '')
    output_plot = f"{base_name}_plot_data.txt"
    output_info = f"{base_name}_info.txt"

    # Parse fitting results
    print(f"Reading data from: {input_filename}")
    data = parse_fitting_results(input_filename)

    if data['a'] is None:
        print("Error: Could not extract fitting parameters from file!")
        sys.exit(1)

    print(f"Successfully extracted {len(data['plot_data'])} data points.")

    # Lattice constant, auto-extracted per direction (Detect-Configuration.py)
    # or manually entered (Manual-Configuration.py)
    lattice = load_lattice_info()
    a_lattice = lattice["lattice_constant_angstrom"]

    DS = data['a']  # Second derivative coefficient
    m_eff = calculate_effective_mass(DS, a_lattice)

    # Write output files
    write_plot_data(output_plot, data['plot_data'])
    write_info_file(output_info, data, m_eff, lattice)

    # Print summary to terminal
    print_summary(data, m_eff, lattice, output_plot, output_info)

if __name__ == "__main__":
    main()
