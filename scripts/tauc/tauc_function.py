#!/usr/bin/env python3
"""Compute the Tauc function from merged absorption-coefficient data.

Port of the user's validated `All-Scripts/2-Tauc-Plots-Calculation.py`, trimmed down from its
generic "ColumnProcessor" configuration scaffold to just the one transformation the pipeline
actually uses, and with the transition-type exponent turned into a real CLI parameter (feature
(a) from the task brief) instead of a hardcoded `2`.

Tauc relation: (alpha * h*nu)^(1/n) vs h*nu, where alpha is in cm^-1 and h*nu in eV.
  n = 2   -> plotted quantity is (alpha*h*nu)^2   -> exponent 2   (direct allowed transition)
  n = 1/2 -> plotted quantity is (alpha*h*nu)^0.5 -> exponent 0.5 (indirect allowed transition)

The eval()-based evaluation approach (restricted namespace, `col1`..`col5` column references)
is kept from the original script so the exponent substitution is the only change to how the
column operations are expressed, per the task's suggested minimal-diff approach.

Input: 5 whitespace-separated columns (Energy(eV), Wavelength(nm), Alpha1, Alpha2, Alpha3), one
optional leading '#' header line -- i.e. the energy-sorted output of `merge_absorption.py`.
Output: same 5 columns, with Alpha1-3 replaced by Tauc-Function1-3, tab-separated, 9 decimals.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd


def _create_namespace(data, headers):
    namespace = {}
    for i, col in enumerate(headers):
        namespace[f'col{i + 1}'] = data.iloc[:, i]
    namespace.update({
        'sqrt': np.sqrt, 'log': np.log, 'log10': np.log10, 'log2': np.log2, 'exp': np.exp,
        'abs': np.abs, 'pi': np.pi, 'e': np.e, 'power': np.power,
    })
    return namespace


def compute_tauc(input_file, output_file, exponent, transition_label=''):
    with open(input_file, 'r') as f:
        lines = f.readlines()
    if not lines:
        raise ValueError(f"{input_file} is empty")

    data_start = 1 if lines[0].strip().startswith('#') else 0
    data_lines = lines[data_start:]
    if not data_lines:
        raise ValueError(f"No data lines found in {input_file}")

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as tmp:
        tmp.writelines(data_lines)
        tmp_name = tmp.name
    try:
        data = pd.read_csv(tmp_name, delim_whitespace=True, header=None)
    finally:
        os.unlink(tmp_name)

    num_cols = data.shape[1]
    if num_cols != 5:
        raise ValueError(
            f"Expected 5 columns (Energy, Wavelength, Alpha1, Alpha2, Alpha3), got {num_cols}"
        )
    headers = [f'Col{i + 1}' for i in range(num_cols)]
    data.columns = headers

    operations = [
        (f"(10**(-12))*((col1*10**4)*col3)**({exponent})", 3),
        (f"(10**(-12))*((col1*10**4)*col4)**({exponent})", 4),
        (f"(10**(-12))*((col1*10**4)*col5)**({exponent})", 5),
    ]

    for operation, target_col in operations:
        namespace = _create_namespace(data, headers)
        result = eval(operation, {"__builtins__": {}}, namespace)
        data.iloc[:, target_col - 1] = result

    custom_header = "# Energy(eV)\tWavelength(nm)\tTauc-Function1\tTauc-Function2\tTauc-Function3"
    with open(output_file, 'w') as f:
        f.write(custom_header + "\n")
        f.write(f"# Exponent used: {exponent} ({transition_label or 'custom'} transition)\n")
        data.to_csv(f, sep='\t', index=False, header=False, float_format='%.9f')

    print(f"Tauc function written to {output_file} (exponent={exponent})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    parser.add_argument('--exponent', type=float, default=2.0,
                         help='2 for direct allowed transitions, 0.5 for indirect allowed transitions')
    parser.add_argument('--transition-label', default='', help='e.g. "Direct" or "Indirect", for the output header comment')
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: input file not found: {args.input_file}")
        sys.exit(1)

    try:
        compute_tauc(args.input_file, args.output_file, args.exponent, args.transition_label)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
