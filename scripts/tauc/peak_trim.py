#!/usr/bin/env python3
"""Peak-detection based trimming of Tauc function data ("Second Approach" only).

Direct port of the user's validated `All-Scripts/3-Tauc-Function-Data-Processor.py` (logic
unchanged, CLI switched to argparse). Not used by the "First Approach" -- see the two shell
drivers this was ported from (`1-Global-Commands-First-Approach.sh` leaves this step commented
out; `2-Global-Commands-Second-Approach.sh` runs it). Both approaches are always produced by
this module's API handler and kept in separate, clearly-labeled output subfolders (feature (g)
from the task brief) rather than making the student pick one.

Steps:
  1. Lower energy cut: drop the leading near-zero noise below a 1e-6 x max threshold.
  2. Peak detection: find the first 3 local maxima per Tauc column via trend-change detection.
  3. Upper energy cut: trim everything after the latest "3rd peak" found across the 3 columns.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd


def find_local_peaks(energy, tauc_values, num_peaks=3):
    if len(energy) < 3:
        return []

    peaks_found = []
    search_start = 0

    for _ in range(num_peaks):
        if search_start >= len(energy) - 2:
            break

        tauc_window = tauc_values[search_start:]
        differences = np.diff(tauc_window)

        positive_trend = True
        first_negative_idx = None
        trend_reversal_idx = None

        for i in range(len(differences)):
            if positive_trend:
                if differences[i] < 0:
                    first_negative_idx = i
                    positive_trend = False
            else:
                if differences[i] > 0:
                    trend_reversal_idx = i
                    break

        if first_negative_idx is None:
            peak_idx = len(tauc_window) - 1
        elif trend_reversal_idx is None:
            peak_idx = np.argmax(tauc_window[:first_negative_idx + 1])
        else:
            peak_idx = np.argmax(tauc_window[:trend_reversal_idx])

        abs_peak_idx = search_start + peak_idx
        peaks_found.append({
            'energy': energy[abs_peak_idx],
            'value': tauc_values[abs_peak_idx],
            'index': abs_peak_idx,
        })
        search_start = abs_peak_idx + 1

    return peaks_found


def apply_threshold_filter(energy, tauc_values, threshold_factor=1e-6):
    max_value = np.max(tauc_values)
    threshold = max_value * threshold_factor
    valid_indices = np.where(tauc_values > threshold)[0]
    if len(valid_indices) == 0:
        return None, None, max_value, threshold
    first_valid_idx = valid_indices[0]
    return first_valid_idx, energy[first_valid_idx], max_value, threshold


def process_tauc_data(input_file, info_file, output_file):
    info_lines = []
    info_lines.append("=" * 70)
    info_lines.append("TAUC DATA PROCESSING REPORT (Second Approach: peak-trim)")
    info_lines.append("=" * 70)
    info_lines.append(f"Input file: {input_file}")
    info_lines.append(f"Info file: {info_file}")
    info_lines.append(f"Output file: {output_file}")
    info_lines.append("")

    header_line = None
    with open(input_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                header_line = line.strip()
                break

    data = pd.read_csv(input_file, sep='\t', comment='#')
    info_lines.append("Successfully loaded data")
    info_lines.append(f"  Original data points: {len(data)}")
    info_lines.append(f"  Energy range: {data.iloc[0, 0]:.6f} - {data.iloc[-1, 0]:.6f} eV")
    info_lines.append("")

    energy = data.iloc[:, 0].values
    tauc1 = data.iloc[:, 2].values
    tauc2 = data.iloc[:, 3].values
    tauc3 = data.iloc[:, 4].values
    column_names = data.columns.tolist()

    info_lines.append("=" * 70)
    info_lines.append("PART 1: LOWER ENERGY CUT (Threshold Filtering)")
    info_lines.append("=" * 70)

    idx1, energy1, max1, thresh1 = apply_threshold_filter(energy, tauc1)
    idx2, energy2, max2, thresh2 = apply_threshold_filter(energy, tauc2)
    idx3, energy3, max3, thresh3 = apply_threshold_filter(energy, tauc3)

    for name, e, mx, th in (('Tauc-Function1', energy1, max1, thresh1),
                             ('Tauc-Function2', energy2, max2, thresh2),
                             ('Tauc-Function3', energy3, max3, thresh3)):
        info_lines.append(f"{name}: max={mx:.6e}, threshold={th:.6e}, "
                           f"first valid energy={'n/a' if e is None else f'{e:.6f} eV'}")

    valid_energies = [e for e in [energy1, energy2, energy3] if e is not None]
    if not valid_energies:
        with open(info_file, 'w') as f:
            f.write('\n'.join(info_lines))
        raise ValueError("No valid points found in any Tauc column above the noise threshold")

    min_valid_energy = min(valid_energies)
    lower_cut_idx = np.where(energy >= min_valid_energy)[0][0]
    info_lines.append(f"\nLower cut at index {lower_cut_idx} (energy {min_valid_energy:.6f} eV)\n")

    data_trimmed = data.iloc[lower_cut_idx:].copy()
    energy_trimmed = energy[lower_cut_idx:]
    tauc1_trimmed = tauc1[lower_cut_idx:]
    tauc2_trimmed = tauc2[lower_cut_idx:]
    tauc3_trimmed = tauc3[lower_cut_idx:]

    info_lines.append("=" * 70)
    info_lines.append("PART 2: PEAK DETECTION")
    info_lines.append("=" * 70)

    peaks1 = find_local_peaks(energy_trimmed, tauc1_trimmed, num_peaks=3)
    peaks2 = find_local_peaks(energy_trimmed, tauc2_trimmed, num_peaks=3)
    peaks3 = find_local_peaks(energy_trimmed, tauc3_trimmed, num_peaks=3)

    for name, peaks in (('Tauc-Function1', peaks1), ('Tauc-Function2', peaks2), ('Tauc-Function3', peaks3)):
        info_lines.append(f"{name}: {len(peaks)} peak(s) found")
        for i, peak in enumerate(peaks, 1):
            info_lines.append(f"  Peak {i}: {peak['energy']:.6f} eV")

    info_lines.append("")
    info_lines.append("=" * 70)
    info_lines.append("PART 3: UPPER ENERGY CUT (After Third Peak)")
    info_lines.append("=" * 70)

    third_peaks = [peaks[2]['energy'] for peaks in (peaks1, peaks2, peaks3) if len(peaks) >= 3]

    if not third_peaks:
        info_lines.append("No third peaks found in any column; keeping all data after lower cut.")
        data_final = data_trimmed
    else:
        max_third_peak_energy = max(third_peaks)
        upper_cut_mask = energy_trimmed <= max_third_peak_energy
        upper_cut_idx = np.where(upper_cut_mask)[0][-1] + 1
        info_lines.append(f"Upper cut at energy {max_third_peak_energy:.6f} eV (index {upper_cut_idx})")
        data_final = data_trimmed.iloc[:upper_cut_idx].copy()

    info_lines.append("")
    info_lines.append("=" * 70)
    info_lines.append("FINAL RESULTS")
    info_lines.append("=" * 70)
    info_lines.append(f"Original points: {len(data)} -> Final points: {len(data_final)}")
    info_lines.append(f"Final energy range: {data_final.iloc[0, 0]:.6f} - {data_final.iloc[-1, 0]:.6f} eV")

    with open(info_file, 'w') as f:
        f.write('\n'.join(info_lines))

    with open(output_file, 'w') as f:
        f.write((header_line or '# ' + '\t'.join(column_names)) + '\n')
        for _, row in data_final.iterrows():
            f.write('\t'.join(f"{val:.9f}" for val in row) + '\n')

    print(f"Peak-trim complete: {len(data)} -> {len(data_final)} points")
    print(f"Info file: {info_file}")
    print(f"Output file: {output_file}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file')
    parser.add_argument('info_file')
    parser.add_argument('output_file')
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: input file not found: {args.input_file}")
        sys.exit(1)

    try:
        process_tauc_data(args.input_file, args.info_file, args.output_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
