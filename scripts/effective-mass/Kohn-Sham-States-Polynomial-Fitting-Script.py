"""
Quadratic fit of one trimmed band (E(k) = ak^2 + bk + c) with scipy, plus the
fit-quality plot. Ported from the validated one-off toolkit
(Kohn-Sham-States-Polynomial-Fitting-Script.py); the analysis itself
(scipy_polynomial_fit_analysis, write_enhanced_results_to_file,
print_enhanced_results) is unchanged.

New in this port (GUI features (c)-(f) from the module spec): create_enhanced_plot
now reads plot settings from material_config.json's settings.plot (written by
Detect-Configuration.py / Manual-Configuration.py from the web form) to
support:
  (c) auto-ranged axis limits (data min/max + 1% padding) with manual override
  (d) figure output format: PNG / LaTeX (pgfplots) / both
  (e) legend customization: per-series labels, position, show/hide
  (f) an optional custom LaTeX template (%%PGFPLOTS_AXIS%% token substitution)
via the shared scripts/common/pgfplots_export.py helper (auto_range,
resolve_range, Curve, export_pgfplots - same helper the Tauc module uses).
"""
import numpy as np
import sys
import os
import json
from datetime import datetime
from scipy.optimize import curve_fit
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Plots will be skipped.")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from pgfplots_export import Curve, export_pgfplots, resolve_range, compile_pgfplots_to_pdf  # noqa: E402

DEFAULT_PLOT_SETTINGS = {
    "x_range": "",
    "y_range": "",
    "legend_show": True,
    "legend_label_data": "DFT data points",
    "legend_label_fit": "Fitted parabola",
    "legend_position": "best",
    "figure_format": "png",
    "template_path": None,
}

# matplotlib understands these loc strings natively except "outside", which
# needs an explicit bbox_to_anchor to place the legend outside the axes.
_MPL_LEGEND_KWARGS = {
    "best": {"loc": "best"},
    "upper right": {"loc": "upper right"},
    "upper left": {"loc": "upper left"},
    "lower right": {"loc": "lower right"},
    "lower left": {"loc": "lower left"},
    "outside": {"loc": "center left", "bbox_to_anchor": (1.02, 0.5)},
}


def load_plot_settings():
    settings = dict(DEFAULT_PLOT_SETTINGS)
    if os.path.exists("material_config.json"):
        try:
            with open("material_config.json") as f:
                config = json.load(f)
            plot = config.get("settings", {}).get("plot", {})
            settings.update(plot)
        except Exception as e:
            print(f"Warning: could not read plot settings from material_config.json: {e}")
    return settings


def quadratic_function(k, a, b, c):
    """
    Quadratic function for fitting: E(k) = ak² + bk + c
    """
    return a * k**2 + b * k + c

def read_band_data(filename):
    """
    Read band structure data from file
    Expected format: two columns (k-value, energy)
    """
    try:
        data = np.loadtxt(filename)
        k_values = data[:, 0]
        energies = data[:, 1]
        return k_values, energies
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return None, None

def scipy_polynomial_fit_analysis(k, E, degree=2):
    """
    Perform polynomial fitting and analysis using SciPy
    """
    try:
        # Perform curve fitting with error estimation
        popt, pcov = curve_fit(quadratic_function, k, E)

        # Extract coefficients
        a, b, c = popt

        # Calculate parameter uncertainties
        param_errors = np.sqrt(np.diag(pcov))
        a_err, b_err, c_err = param_errors

        # Calculate fitted values
        E_fitted = quadratic_function(k, a, b, c)

        # Calculate R² (goodness of fit)
        ss_res = np.sum((E - E_fitted) ** 2)
        ss_tot = np.sum((E - np.mean(E)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        # Calculate additional statistics
        n = len(E)
        dof = n - 3  # degrees of freedom (n - number of parameters)

        # Root Mean Square Error
        rmse = np.sqrt(ss_res / dof)

        # Standard error of the regression
        std_err = np.sqrt(ss_res / dof)

        # Find extremum (minimum or maximum)
        k_extremum = -b / (2 * a)
        E_extremum = quadratic_function(k_extremum, a, b, c)
        second_derivative = 2 * a

        # Determine if it's minimum or maximum
        extremum_type = "minimum" if a > 0 else "maximum"

        # Calculate uncertainty in extremum position
        # Using error propagation: δ(k_ext) = √[(δb/(2a))² + (b·δa/(2a²))²]
        k_extremum_err = np.sqrt((b_err / (2 * a))**2 + (b * a_err / (2 * a**2))**2)

        # Uncertainty in extremum energy
        E_extremum_err = np.sqrt(
            (k_extremum**2 * a_err)**2 +
            (k_extremum * b_err)**2 +
            c_err**2
        )

        # Calculate correlation coefficients
        correlation_matrix = pcov / np.outer(param_errors, param_errors)

        return {
            'coefficients': popt,
            'coefficient_errors': param_errors,
            'covariance_matrix': pcov,
            'correlation_matrix': correlation_matrix,
            'r_squared': r_squared,
            'rmse': rmse,
            'std_error': std_err,
            'degrees_of_freedom': dof,
            'k_extremum': k_extremum,
            'E_extremum': E_extremum,
            'k_extremum_error': k_extremum_err,
            'E_extremum_error': E_extremum_err,
            'second_derivative': second_derivative,
            'extremum_type': extremum_type,
            'fitted_values': E_fitted
        }

    except Exception as e:
        print(f"Error in fitting: {e}")
        return None

def create_enhanced_plot(k, E, results, input_filename, plot_settings, save_plot=True):
    """
    Create and save the fitted curve plot (PNG via matplotlib and/or a LaTeX
    pgfplots source file), honoring the GUI's axis-range/legend/format
    settings.
    """
    figure_format = (plot_settings.get("figure_format") or "png").lower()
    want_png = figure_format in ("png", "both")
    want_latex = figure_format in ("latex", "both")
    legend_show = plot_settings.get("legend_show", True)
    legend_position = plot_settings.get("legend_position", "best")
    label_data = plot_settings.get("legend_label_data") or "DFT data points"
    label_fit = plot_settings.get("legend_label_fit") or "Fitted parabola"

    # Create fitted curve for plotting
    k_fit = np.linspace(k.min(), k.max(), 100)
    E_fit = quadratic_function(k_fit, *results['coefficients'])

    # Calculate confidence bands (approximate)
    a, b, c = results['coefficients']
    a_err, b_err, c_err = results['coefficient_errors']

    # Simple error propagation for confidence bands
    E_fit_err = np.sqrt(
        (k_fit**2 * a_err)**2 +
        (k_fit * b_err)**2 +
        c_err**2
    )

    # (c) Auto-ranged axis limits (data min/max + 1% padding), with manual
    # override via plot_settings["x_range"]/["y_range"] ("min,max" strings;
    # empty string means "auto"). Shared helper also used by the Tauc module.
    xlim = resolve_range(plot_settings.get("x_range"), list(k), pad_frac=0.01)
    ylim = resolve_range(plot_settings.get("y_range"), list(E) + list(E_fit), pad_frac=0.01)

    base_name = os.path.splitext(input_filename)[0]
    saved_files = []

    if want_png:
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib not available. Skipping PNG plot generation.")
        else:
            plt.figure(figsize=(12, 8))

            # Plot original data and fitted curve
            plt.plot(k, E, 'ro', label=label_data, markersize=6, alpha=0.7)
            plt.plot(k_fit, E_fit, 'b-', label=label_fit, linewidth=2)

            # Plot confidence bands
            plt.fill_between(k_fit, E_fit - E_fit_err, E_fit + E_fit_err,
                             alpha=0.3, color='blue', label='±1σ Confidence Band')

            # Mark extremum with error bars
            if results['k_extremum'] is not None:
                plt.errorbar(results['k_extremum'], results['E_extremum'],
                            xerr=results['k_extremum_error'],
                            yerr=results['E_extremum_error'],
                            fmt='gs', markersize=8, capsize=5,
                            label=f'{results["extremum_type"].title()} ± Error')

            # Formatting
            plt.xlabel('k (Å⁻¹)', fontsize=12)
            plt.ylabel('E (eV)', fontsize=12)
            plt.title(f'Band Structure Fit - {os.path.basename(input_filename)}', fontsize=14)
            plt.xlim(xlim)
            plt.ylim(ylim)
            if legend_show:
                plt.legend(fontsize=10, **_MPL_LEGEND_KWARGS.get(legend_position, {"loc": "best"}))
            plt.grid(True, alpha=0.3)

            # Enhanced fit information
            equation_text = (f'E(k) = ({a:.4f}±{a_err:.4f})k² + ({b:.4f}±{b_err:.4f})k + ({c:.4f}±{c_err:.4f})\n'
                            f'R² = {results["r_squared"]:.6f}\n'
                            f'RMSE = {results["rmse"]:.6f} eV')

            plt.text(0.05, 0.95, equation_text, transform=plt.gca().transAxes,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

            plt.tight_layout()

            if save_plot:
                plot_filename = f"{base_name}_scipy_fitting_plot.png"
                plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
                print(f"✓ Plot saved to: {plot_filename}")
                saved_files.append(plot_filename)
            plt.close()

    if want_latex:
        # (d)/(e)/(f): pgfplots export with the same two labeled series, axis
        # range, legend position/visibility, and an optional uploaded
        # template (template_path with a %%PGFPLOTS_AXIS%% token).
        curves = [
            Curve(x=list(k), y=list(E), label=label_data if legend_show else ""),
            Curve(x=list(k_fit), y=list(E_fit), label=label_fit if legend_show else ""),
        ]
        tex_filename = f"{base_name}_scipy_fitting_plot.tex"
        template_path = plot_settings.get("template_path") or None
        dat_paths = export_pgfplots(
            tex_filename,
            curves,
            xlabel=r"k (\AA$^{-1}$)",
            ylabel="E (eV)",
            xlim=xlim,
            ylim=ylim,
            legend=legend_show,
            legend_position=legend_position,
            template_path=template_path,
        )
        print(f"✓ LaTeX (pgfplots) figure saved to: {tex_filename}")
        saved_files.append(tex_filename)
        saved_files.extend(dat_paths)
        pdf_path = compile_pgfplots_to_pdf(tex_filename)
        if pdf_path:
            print(f"✓ Compiled PDF saved to: {pdf_path}")
            saved_files.append(pdf_path)

    return saved_files

def write_enhanced_results_to_file(filename, k, E, results, input_filename):
    """
    Write enhanced analysis results to output file
    """
    with open(filename, 'w') as f:
        f.write("="*70 + "\n")
        f.write("ELECTRONIC BAND STRUCTURE POLYNOMIAL FITTING ANALYSIS (SciPy)\n")
        f.write("="*70 + "\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Input File: {input_filename}\n")
        f.write(f"Number of data points: {len(k)}\n")
        f.write(f"Degrees of freedom: {results['degrees_of_freedom']}\n")
        f.write(f"k-range: {k.min():.6f} to {k.max():.6f}\n")
        f.write(f"Energy range: {E.min():.6f} to {E.max():.6f}\n")
        f.write("\n")

        # Fitted equation with uncertainties
        a, b, c = results['coefficients']
        a_err, b_err, c_err = results['coefficient_errors']

        f.write("FITTED QUADRATIC EQUATION WITH UNCERTAINTIES:\n")
        f.write(f"E(k) = ({a:.8f} ± {a_err:.8f})k² + ({b:.8f} ± {b_err:.8f})k + ({c:.8f} ± {c_err:.8f})\n")
        f.write("\n")

        # Detailed coefficients
        f.write("POLYNOMIAL COEFFICIENTS:\n")
        f.write(f"a (k² coefficient): {a:.8f} ± {a_err:.8f}\n")
        f.write(f"b (k coefficient):  {b:.8f} ± {b_err:.8f}\n")
        f.write(f"c (constant):       {c:.8f} ± {c_err:.8f}\n")
        f.write("\n")

        # Correlation matrix
        f.write("PARAMETER CORRELATION MATRIX:\n")
        f.write("     a      b      c\n")
        corr = results['correlation_matrix']
        f.write(f"a  {corr[0,0]:6.3f} {corr[0,1]:6.3f} {corr[0,2]:6.3f}\n")
        f.write(f"b  {corr[1,0]:6.3f} {corr[1,1]:6.3f} {corr[1,2]:6.3f}\n")
        f.write(f"c  {corr[2,0]:6.3f} {corr[2,1]:6.3f} {corr[2,2]:6.3f}\n")
        f.write("\n")

        # Second derivative and effective mass info
        f.write("SECOND DERIVATIVE:\n")
        f.write(f"∂²E/∂k² = {results['second_derivative']:.8f} ± {2*a_err:.8f}\n")
        f.write("Note: For effective mass calculation, use:\n")
        f.write("m* = ℏ² × (2π/a_lattice)² / |∂²E/∂k²|\n")
        f.write("where a_lattice is the lattice parameter\n")
        f.write("\n")

        # Extremum information with uncertainties
        f.write("EXTREMUM INFORMATION WITH UNCERTAINTIES:\n")
        f.write(f"Type: {results['extremum_type']}\n")
        f.write(f"k-position: {results['k_extremum']:.8f} ± {results['k_extremum_error']:.8f}\n")
        f.write(f"Energy: {results['E_extremum']:.8f} ± {results['E_extremum_error']:.8f}\n")
        f.write("\n")

        # Enhanced fit quality statistics
        f.write("FIT QUALITY STATISTICS:\n")
        f.write(f"R² (coefficient of determination): {results['r_squared']:.8f}\n")
        f.write(f"Root Mean Square Error (RMSE): {results['rmse']:.8f}\n")
        f.write(f"Standard Error of Regression: {results['std_error']:.8f}\n")
        f.write(f"Degrees of Freedom: {results['degrees_of_freedom']}\n")

        if results['r_squared'] > 0.999:
            f.write("✓ Excellent fit (R² > 0.999)\n")
        elif results['r_squared'] > 0.99:
            f.write("✓ Very good fit (R² > 0.99)\n")
        elif results['r_squared'] > 0.95:
            f.write("⚠ Good fit (R² > 0.95)\n")
        else:
            f.write("⚠ Poor fit (R² < 0.95) - consider checking data or using higher degree\n")
        f.write("\n")

        # Data table with residuals and standardized residuals
        f.write("DATA AND FITTED VALUES:\n")
        f.write("k-value\t\tOriginal E\tFitted E\tResidual\tStd. Residual\n")
        f.write("-" * 65 + "\n")
        residuals = E - results['fitted_values']
        std_residuals = residuals / results['std_error']

        for i in range(len(k)):
            f.write(f"{k[i]:.6f}\t{E[i]:.6f}\t{results['fitted_values'][i]:.6f}\t"
                   f"{residuals[i]:.6f}\t{std_residuals[i]:.3f}\n")

def print_enhanced_results(k, E, results, input_filename):
    """
    Print enhanced results to terminal
    """
    print("="*70)
    print("ELECTRONIC BAND STRUCTURE POLYNOMIAL FITTING ANALYSIS (SciPy)")
    print("="*70)
    print(f"Input File: {input_filename}")
    print(f"Number of data points: {len(k)}")
    print(f"Degrees of freedom: {results['degrees_of_freedom']}")
    print(f"k-range: {k.min():.6f} to {k.max():.6f}")
    print(f"Energy range: {E.min():.6f} to {E.max():.6f}")
    print()

    # Fitted equation with uncertainties
    a, b, c = results['coefficients']
    a_err, b_err, c_err = results['coefficient_errors']

    print("FITTED QUADRATIC EQUATION WITH UNCERTAINTIES:")
    print(f"E(k) = ({a:.8f} ± {a_err:.8f})k² + ({b:.8f} ± {b_err:.8f})k + ({c:.8f} ± {c_err:.8f})")
    print()

    print("POLYNOMIAL COEFFICIENTS:")
    print(f"a (k² coefficient): {a:.8f} ± {a_err:.8f}")
    print(f"b (k coefficient):  {b:.8f} ± {b_err:.8f}")
    print(f"c (constant):       {c:.8f} ± {c_err:.8f}")
    print()

    print("SECOND DERIVATIVE:")
    print(f"∂²E/∂k² = {results['second_derivative']:.8f} ± {2*a_err:.8f}")
    print()

    # Extremum information with uncertainties
    print("EXTREMUM INFORMATION WITH UNCERTAINTIES:")
    print(f"Type: {results['extremum_type']}")
    print(f"k-position: {results['k_extremum']:.8f} ± {results['k_extremum_error']:.8f}")
    print(f"Energy: {results['E_extremum']:.8f} ± {results['E_extremum_error']:.8f}")
    print()

    # Enhanced fit quality
    print("FIT QUALITY STATISTICS:")
    print(f"R² (coefficient of determination): {results['r_squared']:.8f}")
    print(f"Root Mean Square Error (RMSE): {results['rmse']:.8f}")
    print(f"Standard Error of Regression: {results['std_error']:.8f}")

    if results['r_squared'] > 0.999:
        print("✓ Excellent fit (R² > 0.999)")
    elif results['r_squared'] > 0.99:
        print("✓ Very good fit (R² > 0.99)")
    elif results['r_squared'] > 0.95:
        print("⚠ Good fit (R² > 0.95)")
    else:
        print("⚠ Poor fit (R² < 0.95) - consider checking data or using higher degree")

def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python script.py <input_data_file>")
        print("Example: python script.py band_data.txt")
        sys.exit(1)

    input_filename = sys.argv[1]

    # Check if input file exists
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found!")
        sys.exit(1)

    # Read data
    print(f"Reading data from: {input_filename}")
    k, E = read_band_data(input_filename)

    if k is None or E is None:
        print("Failed to read data. Exiting.")
        sys.exit(1)

    print(f"Successfully loaded {len(k)} data points.")
    print()

    # Perform enhanced polynomial fitting analysis with SciPy
    print("Performing SciPy curve fitting analysis...")
    results = scipy_polynomial_fit_analysis(k, E, degree=2)

    if results is None:
        print("Fitting failed. Exiting.")
        sys.exit(1)

    # Print results to terminal
    print_enhanced_results(k, E, results, input_filename)

    # Create and save the fit-quality figure(s) (PNG and/or LaTeX, per the
    # GUI's figure-format setting)
    plot_settings = load_plot_settings()
    create_enhanced_plot(k, E, results, input_filename, plot_settings, save_plot=True)

    # Generate output filename
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}_scipy_fitting_results.txt"

    # Write results to file
    write_enhanced_results_to_file(output_filename, k, E, results, input_filename)

    print()
    print(f"✓ Results saved to: {output_filename}")
    print()
    print("EFFECTIVE MASS CALCULATION:")
    print("m* = ℏ² × (2π/a_lattice)² / |∂²E/∂k²|")
    a_err = results['coefficient_errors'][0]
    print(f"where ∂²E/∂k² = {results['second_derivative']:.8f} ± {2*a_err:.8f}")
    print()
    print("Note: This enhanced version provides parameter uncertainties")
    print("      and improved statistical analysis using SciPy!")

if __name__ == "__main__":
    main()
