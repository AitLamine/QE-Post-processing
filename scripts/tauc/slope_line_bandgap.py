#!/usr/bin/env python3
"""
Enhanced Adaptive Tauc Plot Band Gap Analysis Script with Column-Ordered Presentation

This script automatically detects both early absorption edges and near-peak regions,
performs cross-column validation, and presents results in the original file column order.

Key Features:
- Dual-search strategy: early absorption edge + near-peak region
- User-definable manual search ranges via command line (--range start end)
- Cross-column validation and candidate grouping
- Strict R² requirement with reasonable point count
- REVISED: Scoring logic prioritizes fit quality (R²) over peak proximity
- REVISED: Reduced max points for fits to avoid including non-linear data
- IMPROVED: Always presents results in original column order
- IMPROVED: Shows ALL columns regardless of group membership
- Plots linear fit only in valid domain (band gap → fit end)
- Cascading fallback for difficult datasets
- NEW (V14): --electronic-gap VALUE anchors both automatic search windows on this material/
  approach's own DFT electronic gap instead of a raw-peak-derived window, and locates the edge by
  steepest LOCAL SLOPE (dV/dE) rather than raw peak VALUE. Fixes a real, previously-observed
  failure mode where a large unrelated secondary absorption feature (much bigger raw Tauc value,
  but at a much higher/unrelated energy) pulled the automatic search window away from the true
  fundamental edge entirely - this is the recommended way to run the script for any new material,
  not just something applied after the fact to a few hand-identified problem cases. Falls back to
  the original raw-peak-derived behavior unchanged when omitted.

Usage: python3 4-Slope-Line-Calculation-V14.py input_file.txt [output_file.txt]
       [--range start1 end1] [--range start2 end2] [--electronic-gap VALUE]

Author: Enhanced Version with Column-Ordered Presentation & Manual Override
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import sys
import os


# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Data filtering threshold
THRESHOLD_FACTOR = 1e-6

# Band gap physical constraints
BAND_GAP_MIN = 0.1
BAND_GAP_MAX = 10.0

# Plotting options
PLOT_RESULTS = True
SAVE_PLOTS = True
SHOW_PLOTS = False
PLOT_DPI = 300

# Output options
FLOAT_PRECISION = 6
VERBOSE_OUTPUT = True

# Cross-validation settings
GROUPING_TOLERANCE = 0.5  # ±0.5 eV for grouping candidates
MIN_COLUMNS_FOR_GROUP = 2  # Minimum columns needed for valid group

# Absorption onset detection
ONSET_THRESHOLD_FACTOR = 0.05  # 5% of maximum Tauc value

# ============================================================================
# OPTIMIZED QUALITY THRESHOLDS
# ============================================================================

# Strict quality requirements
STRICT_MIN_R_SQUARED = 0.98    # High linearity requirement
STRICT_MIN_POINTS = 5           # Minimum reasonable sample size
STRICT_MAX_POINTS = 8           # Prevent including non-linear regions (Changed from 10)

# Filter out suspiciously perfect fits (likely 2-3 collinear points)
SUSPICIOUS_R_SQUARED = 0.999
SUSPICIOUS_MAX_POINTS = 4

# ============================================================================
# ELECTRONIC-GAP-ANCHORED SEARCH (optional, via --electronic-gap)
# ============================================================================
# Root-cause fix for a documented, recurring failure mode: without an external anchor, both
# automatic search windows (near_peak, early_edge) are defined purely from a raw-VALUE local
# maximum detected on the Tauc curve itself (find_first_local_peak / find_absorption_onset). A
# later, unrelated secondary absorption feature routinely has a much bigger raw Tauc value than
# the true fundamental edge, so the search window silently locks onto it instead - confirmed for
# real (ZnTe's ordinary component: the automatic fit regressed against the flank leading to a
# spurious peak near 4.7 eV, an order of magnitude steeper than every other curve/material, while
# the genuine edge sat near 1.8 eV - documented in update_znx_paper.py's TAUC_EG_DIVERGENCE_
# THRESHOLD_EV / MANUAL_TAUC_FIT_RANGES / _find_near_edge_slope_fit, all of which exist purely as
# downstream patches for this same root problem).
#
# The fix: every material/approach already has an independently-computed electronic (DFT
# band-structure) gap by the time Tauc analysis runs. Since the Tauc/optical gap is physically
# expected to sit at or modestly above that electronic gap (never far below it, and rarely more
# than ~1 eV above it for these direct-gap wurtzite semiconductors), that value is a strong,
# physically-motivated prior for where the TRUE edge must be - independent of whatever the raw
# curve's own shape happens to do further out. When --electronic-gap is supplied, it replaces the
# raw-peak-derived search windows entirely with windows anchored on this known value, so the
# search can never wander past a physically implausible energy no matter how large a later
# secondary feature is.
ELECTRONIC_GAP_SEARCH_MARGIN_EV = 1.0  # upper bound = electronic_gap + this (the "plus ~1 eV")
ELECTRONIC_GAP_LOWER_PAD_EV = 1.0      # lower bound = electronic_gap - this (generous but finite)

# ============================================================================


class AdaptiveParameters:
    """Automatically determine optimal analysis parameters based on data."""
    
    def __init__(self, energy, tauc_values, peak_energy, search_type='near_peak', electronic_gap=None):
        self.energy = energy
        self.tauc_values = tauc_values
        self.peak_energy = peak_energy
        self.n_points = len(energy)
        self.search_type = search_type
        # Physically-anchored prior (DFT electronic gap for this material/approach), or None to
        # fall back to the original raw-peak-derived behavior unchanged - see the
        # ELECTRONIC-GAP-ANCHORED SEARCH block above for why this exists.
        self.electronic_gap = electronic_gap

        # Calculate data characteristics
        self.energy_step = np.median(np.diff(energy))
        self.points_per_ev = 1.0 / self.energy_step if self.energy_step > 0 else 10

        # Determine adaptive parameters
        self.min_points_for_fit = STRICT_MIN_POINTS
        self.max_points_for_fit = STRICT_MAX_POINTS
        self.search_window = self._calculate_search_window()
        self.min_r_squared = STRICT_MIN_R_SQUARED
        self.search_range = self._calculate_search_range()

    def _calculate_search_window(self):
        """Determine maximum window size for linear region search."""
        # Target: capture up to 1 eV range, but respect max points limit
        window = int(self.points_per_ev * 1.0)
        window = max(window, self.max_points_for_fit)
        window = min(window, int(self.n_points * 0.4))
        return window

    def _calculate_search_range(self):
        """Determine energy range to search for linear regions."""
        if self.electronic_gap is not None:
            # Gap-anchored: ignore the raw-peak-derived formulas entirely and define both search
            # windows directly around the known electronic gap, at two different widths so the
            # existing dual-search + cross-validation machinery still has two independent windows
            # to compare (near_peak = the tighter, gap-centered window; early_edge = a window
            # biased slightly earlier/wider, still gap-anchored, not peak-anchored). Neither window
            # can ever extend past electronic_gap + ELECTRONIC_GAP_SEARCH_MARGIN_EV, which is the
            # actual fix for the documented far-secondary-peak failure mode.
            gap = self.electronic_gap
            ceiling = gap + ELECTRONIC_GAP_SEARCH_MARGIN_EV
            floor = max(self.energy.min(), gap - ELECTRONIC_GAP_LOWER_PAD_EV)
            if self.search_type == 'near_peak':
                search_start = max(floor, gap - 0.5)
                search_end = ceiling
            elif self.search_type == 'early_edge':
                search_start = floor
                search_end = min(gap + 0.3, ceiling)
            else:  # manual search types keep their own explicit range (set via set_search_range)
                search_start = self.energy.min()
                search_end = self.energy.max()
            return (search_start, search_end)

        if self.peak_energy is None:
            return (None, None)

        if self.search_type == 'near_peak':
            # Search from (peak - 2 eV) to peak (original method)
            search_start = max(self.energy.min(), self.peak_energy - 2.0)
            search_end = self.peak_energy
        elif self.search_type == 'early_edge':
            # Search from onset to (peak - 0.5 eV)
            search_start = self.peak_energy  # Will be updated by onset detector
            search_end = min(self.peak_energy + 1.5, self.energy.max())
        else: # Covers manual search types
            search_start = self.energy.min()
            search_end = self.energy.max()
        
        return (search_start, search_end)
    
    def set_search_range(self, start, end):
        """Manually set search range."""
        self.search_range = (start, end)
    
    def print_summary(self, search_label=""):
        """Print the adaptive parameters determined."""
        print(f"\n    --- Adaptive Parameters ({search_label}) ---")
        print(f"    Data density: {self.points_per_ev:.1f} points/eV")
        print(f"    Point range for fit: {self.min_points_for_fit}-{self.max_points_for_fit}")
        print(f"    Minimum R²: {self.min_r_squared}")
        if self.search_range[0] is not None:
            print(f"    Search range: {self.search_range[0]:.3f} - {self.search_range[1]:.3f} eV")


class TaucAnalyzer:
    """Class to analyze Tauc plot data and determine band gaps."""
    
    def __init__(self, filename, manual_ranges=None, electronic_gap=None):
        """Initialize with data file and optional manual search ranges. electronic_gap (eV), when
        given, anchors both automatic search windows on this material/approach's own DFT
        electronic gap instead of a raw-peak-derived window - see the ELECTRONIC-GAP-ANCHORED
        SEARCH config block for why."""
        self.filename = filename
        self.manual_ranges = manual_ranges if manual_ranges else []
        self.electronic_gap = electronic_gap
        self.data = None
        self.tauc_columns = []  # Store original column order
        self.column_candidates = {}  # Store multiple candidates per column
        self.grouped_results = []     # Store cross-validated groups
        self.column_group_map = {}    # Map column to group number
        self.load_data()
    
    def load_data(self):
        """Load Tauc plot data from file."""
        try:
            # Read with space as separator, no header, and assign generic column names
            self.data = pd.read_csv(self.filename, sep=r'\s+', comment='#', header=None) # Fixed: sep=r'\s+'
            # Assign generic column names
            new_columns = {0: 'Energy(eV)'}
            for i in range(1, self.data.shape[1]):
                new_columns[i] = f'col_{i}'
            self.data.rename(columns=new_columns, inplace=True)
            
            print(f"✓ Loaded data from: {self.filename}")
            print(f"✓ Data shape: {self.data.shape}")
            print(f"✓ Columns: {list(self.data.columns)}")
            print(f"✓ Energy range: {self.data.iloc[:, 0].min():.3f} - {self.data.iloc[:, 0].max():.3f} eV")
            
        except Exception as e:
            print(f"✗ Error loading data: {e}")
            sys.exit(1)
    
    def filter_data(self, energy, tauc_values):
        """Apply threshold filtering to remove small fluctuations."""
        max_tauc = np.max(tauc_values)
        threshold = max_tauc * THRESHOLD_FACTOR

        valid_indices = tauc_values > threshold
        filtered_energy = energy[valid_indices]
        filtered_tauc = tauc_values[valid_indices]

        return filtered_energy, filtered_tauc, threshold

    def find_absorption_edge_by_slope(self, energy, tauc_values, lo, hi):
        """Locates the true absorption EDGE within [lo, hi] by its own rate-of-rise shape, not its
        raw VALUE - the direct fix for "locate the edge, not just search for the max value"
        (find_first_local_peak instead tracks raw VALUE, which a later, larger, unrelated
        secondary feature can dominate even though the fundamental edge sits at a lower energy).

        Specifically looks for a genuine LOCAL MAXIMUM in the derivative dV/dE (a "shoulder" -
        the rate of rise itself increases, then decreases, even if the curve's own value never
        turns over) rather than simply the single largest derivative value in the window: a curve
        that is still monotonically accelerating toward a later, unrelated feature has its
        steepest point trivially sit at the window's own upper boundary, which is NOT a real local
        feature and reproduces the same "search grabs whatever is stated" failure this function
        exists to avoid. Verified against a real, previously hand-diagnosed case (ZnTe DFT+U's
        ordinary component): a genuine shoulder sits at ~1.87 eV where dV/dE rises then falls back
        down, well before a much larger, unrelated feature further out that a plain argmax would
        otherwise land on.

        Prefers the FIRST (lowest-energy) genuine shoulder in the window - the earliest sign of a
        rise-then-slow-down pattern, i.e. the fundamental absorption onset, rather than any later
        secondary transition. Falls back to the single steepest point only if the window's
        derivative is monotonically increasing throughout (no genuine shoulder exists to find).
        Returns the edge energy, or None if fewer than 5 points fall in [lo, hi]."""
        mask = (energy >= lo) & (energy <= hi)
        if np.sum(mask) < 5:
            return None
        e_win = energy[mask]
        v_win = tauc_values[mask]
        deriv = np.diff(v_win) / np.diff(e_win)
        if len(deriv) < 3:
            return None
        mid_e = (e_win[:-1] + e_win[1:]) / 2
        shoulders = [
            i for i in range(1, len(deriv) - 1)
            if deriv[i] > deriv[i - 1] and deriv[i] >= deriv[i + 1]
        ]
        if shoulders:
            return float(mid_e[shoulders[0]])
        return float(mid_e[np.argmax(deriv)])

    def find_first_local_peak(self, energy, tauc_values):
        """Find the first local maximum using trend change detection."""
        if len(energy) < 3:
            return None
        
        differences = np.diff(tauc_values)
        
        state = 'searching_for_negative'
        first_negative_idx = None
        reversal_idx = None
        
        for i in range(len(differences)):
            diff = differences[i]
            
            if state == 'searching_for_negative':
                if diff < 0:
                    first_negative_idx = i
                    state = 'found_negative'
                    
            elif state == 'found_negative':
                if diff > 0:
                    reversal_idx = i
                    state = 'found_reversal'
                    break
        
        if reversal_idx is not None:
            search_end_idx = reversal_idx
        elif first_negative_idx is not None:
            search_end_idx = len(tauc_values)
        else:
            search_end_idx = len(tauc_values)
        
        peak_idx = np.argmax(tauc_values[:search_end_idx])
        peak_energy = energy[peak_idx]
        peak_value = tauc_values[peak_idx]
        
        return {
            'peak_energy': peak_energy,
            'peak_value': peak_value,
            'peak_idx': peak_idx
        }
    
    def find_absorption_onset(self, energy, tauc_values, peak_energy):
        """
        Find where absorption starts rising significantly.
        Returns energy where Tauc exceeds threshold AND slope is sustained positive.
        """
        max_tauc = np.max(tauc_values)
        threshold = max_tauc * ONSET_THRESHOLD_FACTOR
        
        # Find where Tauc first exceeds threshold with sustained increase
        for i in range(len(tauc_values) - 3):
            if tauc_values[i] > threshold:
                # Check if next few points also increasing (sustained rise)
                if (tauc_values[i+1] > tauc_values[i] and 
                    tauc_values[i+2] > tauc_values[i+1] and
                    tauc_values[i+3] > tauc_values[i+2]):
                    
                    # Make sure it's before the peak
                    if energy[i] < peak_energy - 0.3:  # At least 0.3 eV before peak
                        print(f"    Absorption onset detected at: {energy[i]:.3f} eV")
                        return energy[i]
        
        # Fallback: return point at 10% of max if no clear onset
        for i in range(len(tauc_values)):
            if tauc_values[i] > max_tauc * 0.10:
                if energy[i] < peak_energy - 0.3:
                    print(f"    Fallback onset (10% threshold) at: {energy[i]:.3f} eV")
                    return energy[i]
        
        print(f"    No clear onset found, using data start")
        return energy[0]
    
    def find_best_linear_region(self, energy, tauc_values, adaptive_params, 
                                min_r_squared_override=None, min_points_override=None):
        """
        Find the best linear region using optimized scoring strategy.
        PRIORITIZES STEEPNESS for early_edge searches to favor true absorption onset.
        """
        
        # Use overrides for fallback attempts
        min_r_squared = min_r_squared_override if min_r_squared_override else adaptive_params.min_r_squared
        min_points = min_points_override if min_points_override else adaptive_params.min_points_for_fit
        max_points = adaptive_params.max_points_for_fit
        
        # Apply search range constraints
        search_start_energy, search_end_energy = adaptive_params.search_range
        
        if search_start_energy is None:
            search_mask = np.ones(len(energy), dtype=bool)
        else:
            search_mask = (energy >= search_start_energy) & (energy <= search_end_energy)
        
        if not np.any(search_mask):
            print(f"    ✗ No data points in search range")
            return None
        
        search_indices = np.where(search_mask)[0]
        search_start_idx = search_indices[0]
        search_end_idx = search_indices[-1] + 1
        available_points = search_end_idx - search_start_idx
        
        print(f"    Searching in: {energy[search_start_idx]:.3f} - {energy[search_end_idx-1]:.3f} eV")
        print(f"    Available points: {available_points}")
        
        # Check if we have enough points
        if available_points < min_points:
            print(f"    ⚠ Only {available_points} points available")
            if available_points >= 3:
                min_points = max(3, available_points - 1)
            else:
                print(f"    ✗ Insufficient data (< 3 points)")
                return None
        
        # STAGE 1: Generate all possible candidates
        raw_candidates = []
        
        for start in range(search_start_idx, search_end_idx - min_points + 1):
            max_window = min(max_points + 1, search_end_idx - start + 1)
            
            for window_size in range(min_points, max_window):
                end = start + window_size
                
                if end > search_end_idx:
                    break
                
                energy_window = energy[start:end]
                tauc_window = tauc_values[start:end]
                
                try:
                    slope, intercept, r_value, p_value, std_err = stats.linregress(energy_window, tauc_window)
                    r_squared = r_value ** 2
                except:
                    continue
                
                # Require positive slope
                if slope <= 0:
                    continue
                
                # Calculate band gap
                band_gap = -intercept / slope if slope != 0 else float('inf')
                
                # Physical constraints
                if not (BAND_GAP_MIN <= band_gap <= BAND_GAP_MAX):
                    continue
                
                # Calculate proximity to peak
                distance_to_peak = abs(energy_window[-1] - adaptive_params.peak_energy) if adaptive_params.peak_energy else 0
                
                raw_candidates.append({
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_squared,
                    'p_value': p_value,
                    'start_index': start,
                    'end_index': end,
                    'energy_range': energy_window,
                    'tauc_range': tauc_window,
                    'band_gap': band_gap,
                    'n_points': len(energy_window),
                    'distance_to_peak': distance_to_peak
                })
        
        if not raw_candidates:
            print(f"    ✗ No candidates generated")
            return None
        
        print(f"    Generated {len(raw_candidates)} raw candidates")
        
        # STAGE 2: Filter by quality thresholds
        quality_candidates = []
        
        for candidate in raw_candidates:
            # Filter by R²
            if candidate['r_squared'] < min_r_squared:
                continue
            
            # Filter by point count
            if candidate['n_points'] < min_points or candidate['n_points'] > max_points:
                continue
            
            # Filter suspicious perfect fits
            if candidate['r_squared'] > SUSPICIOUS_R_SQUARED and candidate['n_points'] <= SUSPICIOUS_MAX_POINTS:
                continue
            
            quality_candidates.append(candidate)
        
        print(f"    After filtering: {len(quality_candidates)} quality candidates")
        
        # STAGE 3: Cascading fallback if no candidates
        if not quality_candidates:
            print(f"    ℹ️ No candidates met quality thresholds, attempting fallback...")
            
            # Fallback 1: Relax R² to 0.95
            if min_r_squared > 0.95 and not min_r_squared_override:
                print(f"    Fallback 1: Relaxing R² to 0.95")
                return self.find_best_linear_region(energy, tauc_values, adaptive_params, 
                                                    min_r_squared_override=0.95, min_points_override=min_points)
            
            # Fallback 2: Relax R² to 0.90
            elif min_r_squared > 0.90:
                print(f"    Fallback 2: Relaxing R² to 0.90")
                return self.find_best_linear_region(energy, tauc_values, adaptive_params, 
                                                    min_r_squared_override=0.90, min_points_override=max(7, min_points))
            
            else:
                print(f"    ✗ No acceptable linear regions found after all fallback attempts")
                return None
        
        # STAGE 4: Score and select best candidate
        def scoring_function(candidate):
            if adaptive_params.search_type == 'early_edge':
                # FOR EARLY EDGE: Prioritize steep slopes (true absorption onset)
                slope_score = min(candidate['slope'] * 5000, 1000)  # Dominant factor
                r2_score = candidate['r_squared'] * 500  # Secondary
                length_penalty = candidate['n_points'] * 2  # Penalize long regions
                total_score = slope_score + r2_score - length_penalty
            else:
                # FOR NEAR PEAK & MANUAL: New scoring - Prioritize R² and ideal point count
                # This logic removes the bias towards the peak and focuses on quality of fit.
                IDEAL_POINTS = 7
                
                # Heavily weight R² - use a power to make it very sensitive at the high end
                r2_score = (candidate['r_squared'] ** 4) * 2000
                
                # Penalize fits that are too long or too short, aiming for the "sweet spot"
                point_penalty = ((candidate['n_points'] - IDEAL_POINTS) ** 2) * 10
                
                total_score = r2_score - point_penalty
            
            return total_score
        
        best_candidate = max(quality_candidates, key=scoring_function)
        
        print(f"    ✓ Selected candidate:")
        print(f"      Energy range: {best_candidate['energy_range'][0]:.3f} - {best_candidate['energy_range'][-1]:.3f} eV")
        print(f"      Points: {best_candidate['n_points']}, R²: {best_candidate['r_squared']:.4f}")
        print(f"      Slope: {best_candidate['slope']:.4f}, Band gap: {best_candidate['band_gap']:.3f} eV")
        
        return best_candidate
    
    def analyze_column(self, column_name):
        """Analyze a single Tauc function column with dual-search strategy."""
        print(f"\n{'='*60}")
        print(f"Analyzing: {column_name}")
        print('='*60)
        
        # Extract data
        energy = self.data['Energy(eV)'].values # Use named column
        tauc_values = self.data[column_name].values
        
        # Filter data
        filtered_energy, filtered_tauc, threshold = self.filter_data(energy, tauc_values)
        
        print(f"Filtering: {len(energy)} → {len(filtered_energy)} points (threshold: {threshold:.2e})")
        
        if len(filtered_energy) < 5:
            print(f"✗ Insufficient data after filtering")
            return []
        
        # Find first peak (raw-value trend-change detector - still used for reporting/validation,
        # but NOT for defining search windows when electronic_gap is available, see below).
        first_peak = self.find_first_local_peak(filtered_energy, filtered_tauc)

        if first_peak:
            print(f"First peak detected: {first_peak['peak_energy']:.3f} eV")
            peak_energy = first_peak['peak_energy']
        else:
            print(f"⚠ No distinct peak detected")
            peak_energy = filtered_energy[np.argmax(filtered_tauc)]

        # ---- Electronic-gap-anchored edge location (the actual fix) ----
        # When available, locate the genuine absorption EDGE by steepest local slope (dV/dE)
        # within [gap - pad, gap + margin], rather than trusting the raw-VALUE peak above, which
        # can sit at a completely different, unrelated energy if the curve has a larger secondary
        # feature further out. This edge estimate becomes the anchor used for both validation
        # (replacing `first_peak` below) and print diagnostics; the actual SEARCH windows
        # themselves are anchored on electronic_gap directly (see AdaptiveParameters._calculate_
        # search_range), not on this edge estimate, so a slightly-off slope estimate can't distort
        # the window the way a spurious raw peak previously could.
        edge_anchor = None
        if self.electronic_gap is not None:
            gap = self.electronic_gap
            edge_lo = max(filtered_energy.min(), gap - ELECTRONIC_GAP_LOWER_PAD_EV)
            edge_hi = gap + ELECTRONIC_GAP_SEARCH_MARGIN_EV
            edge_anchor = self.find_absorption_edge_by_slope(filtered_energy, filtered_tauc, edge_lo, edge_hi)
            if edge_anchor is not None:
                print(f"Electronic gap hint: {gap:.3f} eV -> steepest-slope edge located at "
                      f"{edge_anchor:.3f} eV (search window: {edge_lo:.3f}-{edge_hi:.3f} eV)")
                first_peak = {'peak_energy': edge_anchor, 'peak_value': None, 'index': None}
            else:
                print(f"Electronic gap hint: {gap:.3f} eV, but no steepest-slope edge found in "
                      f"{edge_lo:.3f}-{edge_hi:.3f} eV - falling back to raw-peak validation")

        candidates = []

        # ========== SEARCH 0: EDGE SHOULDER (tight window around the detected shoulder) ==========
        # Only runs when electronic_gap is set AND a genuine shoulder was found. The wider
        # gap-anchored windows below (SEARCH 1/2) still run the full R²-argmax candidate search
        # over their whole span, which can still prefer a *different*, better-R² linear segment
        # elsewhere in that span even once it's properly capped - confirmed by a real test run
        # (ZnTe DFT+U ordinary: the wide near_peak/early_edge windows kept selecting a segment
        # near 2.1-2.8 eV, R²>0.99, even though the genuine shoulder sat at ~1.87 eV). Fitting a
        # TIGHT window directly around the shoulder removes that ambiguity entirely - this mirrors
        # the tight, hand-verified manual override window that was previously needed for this
        # exact case (1.828-1.94 eV), but derives it automatically from the shoulder location
        # instead of a hardcoded per-material lookup.
        if edge_anchor is not None:
            print(f"\n  >>> SEARCH 0: Edge shoulder (tight window) <<<")
            shoulder_half_width = 0.2
            shoulder_lo = max(filtered_energy.min(), edge_anchor - shoulder_half_width)
            shoulder_hi = edge_anchor + shoulder_half_width
            adaptive_params_shoulder = AdaptiveParameters(filtered_energy, filtered_tauc,
                                                            edge_anchor, 'edge_shoulder')
            adaptive_params_shoulder.set_search_range(shoulder_lo, shoulder_hi)
            adaptive_params_shoulder.print_summary("Edge Shoulder")
            linear_fit_shoulder = self.find_best_linear_region(filtered_energy, filtered_tauc,
                                                                 adaptive_params_shoulder)
            if linear_fit_shoulder:
                result_shoulder = self._create_result_dict(column_name, linear_fit_shoulder, filtered_energy,
                                                             filtered_tauc, energy, tauc_values, first_peak,
                                                             adaptive_params_shoulder, 'edge_shoulder')
                candidates.append(result_shoulder)
                print(f"  ✓ Edge-shoulder candidate: Eg = {linear_fit_shoulder['band_gap']:.3f} eV")
            else:
                print(f"  ✗ No edge-shoulder candidate found in tight window "
                      f"{shoulder_lo:.3f}-{shoulder_hi:.3f} eV")

        # ========== SEARCH 1: NEAR PEAK / GAP-ANCHORED (Automatic) ==========
        print(f"\n  >>> SEARCH 1: Near-peak region <<<")
        adaptive_params_peak = AdaptiveParameters(filtered_energy, filtered_tauc, peak_energy,
                                                   'near_peak', electronic_gap=self.electronic_gap)
        adaptive_params_peak.print_summary("Near Peak")

        linear_fit_peak = self.find_best_linear_region(filtered_energy, filtered_tauc, adaptive_params_peak)

        if linear_fit_peak:
            result_peak = self._create_result_dict(column_name, linear_fit_peak, filtered_energy,
                                                   filtered_tauc, energy, tauc_values, first_peak,
                                                   adaptive_params_peak, 'near_peak')
            candidates.append(result_peak)
            print(f"  ✓ Near-peak candidate: Eg = {linear_fit_peak['band_gap']:.3f} eV")
        else:
            print(f"  ✗ No near-peak candidate found")

        # ========== SEARCH 2: EARLY ABSORPTION EDGE (Automatic) ==========
        print(f"\n  >>> SEARCH 2: Early absorption edge <<<")

        if self.electronic_gap is not None:
            # Gap-anchored: AdaptiveParameters computes its own (still gap-anchored, slightly
            # earlier/wider) window internally - no raw onset-detection needed or wanted here.
            adaptive_params_onset = AdaptiveParameters(filtered_energy, filtered_tauc, peak_energy,
                                                        'early_edge', electronic_gap=self.electronic_gap)
            adaptive_params_onset.print_summary("Early Edge")
            linear_fit_onset = self.find_best_linear_region(filtered_energy, filtered_tauc, adaptive_params_onset)
            if linear_fit_onset:
                is_different = True
                if linear_fit_peak:
                    eg_diff = abs(linear_fit_onset['band_gap'] - linear_fit_peak['band_gap'])
                    if eg_diff < 0.1:
                        is_different = False
                        print(f"  ⚠ Early edge candidate too similar to near-peak (ΔEg = {eg_diff:.3f} eV), skipping")
                if is_different:
                    result_onset = self._create_result_dict(column_name, linear_fit_onset, filtered_energy,
                                                           filtered_tauc, energy, tauc_values, first_peak,
                                                           adaptive_params_onset, 'early_edge')
                    candidates.append(result_onset)
                    print(f"  ✓ Early edge candidate: Eg = {linear_fit_onset['band_gap']:.3f} eV")
            else:
                print(f"  ✗ No early edge candidate found")
        else:
            # Find absorption onset
            onset_energy = self.find_absorption_onset(filtered_energy, filtered_tauc, peak_energy)

            # Only search for early edge if onset is significantly before peak
            if onset_energy < peak_energy - 0.5:
                adaptive_params_onset = AdaptiveParameters(filtered_energy, filtered_tauc, onset_energy, 'early_edge')
                # Set search range: from onset to (peak - 0.5 eV)
                search_end = min(onset_energy + 1.5, peak_energy - 0.3)
                adaptive_params_onset.set_search_range(onset_energy, search_end)
                adaptive_params_onset.print_summary("Early Edge")

                linear_fit_onset = self.find_best_linear_region(filtered_energy, filtered_tauc, adaptive_params_onset)

                if linear_fit_onset:
                    # Check if this is different from peak candidate
                    is_different = True
                    if linear_fit_peak:
                        eg_diff = abs(linear_fit_onset['band_gap'] - linear_fit_peak['band_gap'])
                        if eg_diff < 0.1:  # Too similar, probably same region
                            is_different = False
                            print(f"  ⚠ Early edge candidate too similar to near-peak (ΔEg = {eg_diff:.3f} eV), skipping")

                    if is_different:
                        result_onset = self._create_result_dict(column_name, linear_fit_onset, filtered_energy,
                                                               filtered_tauc, energy, tauc_values, first_peak,
                                                               adaptive_params_onset, 'early_edge')
                        candidates.append(result_onset)
                        print(f"  ✓ Early edge candidate: Eg = {linear_fit_onset['band_gap']:.3f} eV")
                else:
                    print(f"  ✗ No early edge candidate found")
            else:
                print(f"  ⚠ Onset too close to peak ({onset_energy:.3f} vs {peak_energy:.3f}), skipping early edge search")

        # ========== SEARCH 3+: MANUAL RANGES ==========
        if self.manual_ranges:
            for i, (start_range, end_range) in enumerate(self.manual_ranges, 1):
                search_label = f'manual_{i}'
                print(f"\n  >>> SEARCH {2+i}: Manual Range {i} <<<")
                
                adaptive_params_manual = AdaptiveParameters(filtered_energy, filtered_tauc, peak_energy, search_label)
                adaptive_params_manual.set_search_range(start_range, end_range)
                adaptive_params_manual.print_summary(f"Manual {i}")

                linear_fit_manual = self.find_best_linear_region(filtered_energy, filtered_tauc, adaptive_params_manual)

                if linear_fit_manual:
                    result_manual = self._create_result_dict(column_name, linear_fit_manual, filtered_energy,
                                                               filtered_tauc, energy, tauc_values, first_peak,
                                                               adaptive_params_manual, search_label)
                    candidates.append(result_manual)
                    print(f"  ✓ Manual candidate {i}: Eg = {linear_fit_manual['band_gap']:.3f} eV")
                else:
                    print(f"  ✗ No candidate found in manual range {i}")

        print(f"\n  Total candidates for {column_name}: {len(candidates)}")
        
        return candidates
    
    def _create_result_dict(self, column_name, linear_fit, filtered_energy, filtered_tauc,
                           original_energy, original_tauc, first_peak, adaptive_params, search_type):
        """Create standardized result dictionary."""
        band_gap = linear_fit['band_gap']
        
        # Format equation
        slope_val = linear_fit['slope']
        intercept_val = linear_fit['intercept']
        
        if intercept_val >= 0:
            equation_str = f"Tauc(E) = {slope_val:.4f}×E + {intercept_val:.4f}"
        else:
            equation_str = f"Tauc(E) = {slope_val:.4f}×E - {abs(intercept_val):.4f}"
        
        energy_range_str = f"{linear_fit['energy_range'][0]:.3f} - {linear_fit['energy_range'][-1]:.3f} eV"
        
        # Validation
        peak_energy = first_peak['peak_energy'] if first_peak else None
        validation_status, validation_message = self.validate_band_gap(band_gap, peak_energy)
        
        return {
            'column': column_name,
            'search_type': search_type,
            'band_gap': band_gap,
            'slope': linear_fit['slope'],
            'intercept': linear_fit['intercept'],
            'equation': equation_str,
            'energy_range_str': energy_range_str,
            'r_squared': linear_fit['r_squared'],
            'p_value': linear_fit['p_value'],
            'n_points': linear_fit['n_points'],
            'energy_min': linear_fit['energy_range'][0],
            'energy_max': linear_fit['energy_range'][-1],
            'linear_energy_range': linear_fit['energy_range'],
            'linear_tauc_range': linear_fit['tauc_range'],
            'filtered_energy': filtered_energy,
            'filtered_tauc': filtered_tauc,
            'original_energy': original_energy,
            'original_tauc': original_tauc,
            'first_peak': first_peak,
            'validation_status': validation_status,
            'validation_message': validation_message,
            'adaptive_params': adaptive_params
        }
    
    def validate_band_gap(self, band_gap, peak_energy):
        """Validate that band gap is physically reasonable relative to peak."""
        if peak_energy is None or band_gap is None:
            return "NOT_VALIDATED", "Peak not detected"
        
        gap_to_peak = peak_energy - band_gap
        
        if gap_to_peak < -0.1:
            return "FAILED", f"Eg ({band_gap:.3f}) > Peak ({peak_energy:.3f}) ✗ [Invalid]"
        elif gap_to_peak < 0.1:
            return "WARNING", f"Eg ({band_gap:.3f}) ≈ Peak ({peak_energy:.3f}) ⚠ [Δ = {gap_to_peak:.3f} eV]"
        elif gap_to_peak < 0.8:
            return "PASSED", f"Eg ({band_gap:.3f}) < Peak ({peak_energy:.3f}) ✓ [Δ = {gap_to_peak:.3f} eV]"
        else:
            return "WARNING", f"Eg ({band_gap:.3f}) far from Peak ({peak_energy:.3f}) ⚠ [Δ = {gap_to_peak:.3f} eV]"
    
    def analyze_all_columns(self):
        """Analyze all Tauc function columns with dual-search strategy."""
        print("=" * 60)
        print("ENHANCED ADAPTIVE TAUC PLOT ANALYSIS")
        print("Dual-Search Strategy + Manual Override")
        print("=" * 60)
        
        # Find Tauc columns (preserve order)
        # Assuming first column is Energy(eV), and the second is Wavelength(nm)
        # We want to process only the last three columns, which correspond to Tauc-Function1, Tauc-Function2, Tauc-Function3
        tauc_columns = self.data.columns[2:].tolist() # Selects columns from index 2 onwards
        
        self.tauc_columns = tauc_columns  # Store original order
        print(f"Columns to analyze (in file order): {tauc_columns}\n")
        
        # Analyze each column
        for column in tauc_columns:
            candidates = self.analyze_column(column)
            if candidates:
                self.column_candidates[column] = candidates
        
        # Cross-validate results
        if self.column_candidates:
            self.cross_validate_results()
    
    def cross_validate_results(self):
        """Perform cross-column validation and create column-to-group mapping."""
        print("\n" + "="*60)
        print("CROSS-COLUMN VALIDATION")
        print("="*60)
        
        # Flatten all candidates
        all_candidates = []
        for column, candidates in self.column_candidates.items():
            for candidate in candidates:
                all_candidates.append(candidate)
        
        print(f"\nTotal candidates across all columns: {len(all_candidates)}")
        
        # Group by proximity
        groups = self.group_by_proximity(all_candidates, GROUPING_TOLERANCE)
        
        print(f"Candidates grouped into {len(groups)} group(s) (tolerance: ±{GROUPING_TOLERANCE} eV)")
        
        # Rank groups
        total_columns = len(self.tauc_columns)
        ranked_groups = self.rank_groups(groups, total_columns)
        
        self.grouped_results = ranked_groups
        
        # Create column-to-group mapping
        self._create_column_group_map()
        
        # Display results (column-ordered)
        self.display_results_by_column()
    
    def _create_column_group_map(self):
        """Create mapping of columns to their group numbers."""
        self.column_group_map = {}
        
        for group_idx, group_info in enumerate(self.grouped_results, 1):
            for candidate in group_info['group']:
                col = candidate['column']
                if col not in self.column_group_map:
                    self.column_group_map[col] = []
                # Add group_idx only if not already present to avoid duplicates
                if group_idx not in self.column_group_map[col]:
                    self.column_group_map[col].append(group_idx)
    
    def group_by_proximity(self, candidates, tolerance):
        """Group candidates with similar Eg values."""
        groups = []
        used_indices = set()
        
        # Sort by band gap for easier grouping
        sorted_candidates = sorted(enumerate(candidates), key=lambda x: x[1]['band_gap'])
        
        for i, (idx1, cand1) in enumerate(sorted_candidates):
            if idx1 in used_indices:
                continue
            
            group = [cand1]
            used_indices.add(idx1)
            
            for j, (idx2, cand2) in enumerate(sorted_candidates):
                if idx2 in used_indices:
                    continue
                
                # Determine tolerance based on whether candidates are manual
                current_tolerance = tolerance
                # If any candidate is manual, use a stricter tolerance for grouping with others
                # or allow wider grouping if both are manual and user wants to see them together
                # For now, let's keep it simple: manual candidates are grouped if very close
                if 'manual' in cand1['search_type'] or 'manual' in cand2['search_type']:
                    current_tolerance = 0.1 # Stricter tolerance for manual candidates to group with others

                if abs(cand1['band_gap'] - cand2['band_gap']) <= current_tolerance:
                    group.append(cand2)
                    used_indices.add(idx2)
            
            groups.append(group)
        
        return groups
    
    def rank_groups(self, groups, total_columns):
        """Rank groups by consistency and quality, prioritizing absorption edge and manual inputs."""
        scored_groups = []
        
        for group in groups:
            # Count unique columns represented
            columns_in_group = len(set(c['column'] for c in group))
            
            # Check if it's a group primarily formed by manual candidates
            is_manual_group_dominant = sum(1 for c in group if 'manual' in c['search_type']) > (len(group) / 2)

            # Skip groups with insufficient column representation unless it's a manual group
            if not is_manual_group_dominant and columns_in_group < min(MIN_COLUMNS_FOR_GROUP, total_columns):
                continue
            
            # Calculate metrics
            eg_values = [c['band_gap'] for c in group]
            eg_mean = np.mean(eg_values)
            eg_std = np.std(eg_values)
            eg_range = max(eg_values) - min(eg_values)
            avg_r2 = np.mean([c['r_squared'] for c in group])
            avg_slope = np.mean([c['slope'] for c in group])
            
            # Count search types
            early_edge_count = sum(1 for c in group if c['search_type'] == 'early_edge')
            manual_count = sum(1 for c in group if 'manual' in c['search_type'])
            # edge_shoulder candidates come from a tight window fit directly around a genuine
            # local-max-in-slope shoulder (see SEARCH 0 / find_absorption_edge_by_slope) - the
            # most physically-motivated automatic candidate available when an electronic-gap
            # anchor is supplied, so weighted similarly to a manual override rather than treated
            # as an ordinary automatic candidate.
            edge_shoulder_count = sum(1 for c in group if c['search_type'] == 'edge_shoulder')

            # Scoring
            base_score = (columns_in_group * 100) + (avg_r2 * 50) - (eg_range * 10) + (avg_slope * 5)
            edge_bonus = (early_edge_count / len(group)) * 500
            manual_bonus = (manual_count / len(group)) * 1000 # Heavily prioritize manual groups
            edge_shoulder_bonus = (edge_shoulder_count / len(group)) * 900
            eg_penalty = eg_mean * 10

            final_score = base_score + edge_bonus + manual_bonus + edge_shoulder_bonus - eg_penalty
            
            scored_groups.append({
                'group': group,
                'score': final_score,
                'columns': columns_in_group,
                'eg_mean': eg_mean,
                'eg_std': eg_std,
                'eg_range': eg_range,
                'avg_r2': avg_r2,
                'avg_slope': avg_slope,
                'early_edge_count': early_edge_count,
                'manual_count': manual_count,
            })
        
        # Sort by score (highest first)
        scored_groups.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_groups
    
    def display_results_by_column(self):
        """Display results organized by original column order."""
        if not self.column_candidates:
            print("\n⚠ No valid candidates found in any column.")
            return

        print("\n" + "="*60)
        print("RESULTS BY COLUMN (Original File Order)")
        print("="*60)
        
        # Display summary for each column in original order
        for column in self.tauc_columns:
            print("\n" + "─"*60)
            print(f"COLUMN: {column}")
            print("─"*60)
            
            if column not in self.column_candidates:
                print("  ✗ No results found for this column")
                continue
            
            candidates = self.column_candidates[column]
            groups = self.column_group_map.get(column, [])
            
            if not groups:
                print("  ⚠ Results found but not grouped (outside tolerance)")
            else:
                group_str = ", ".join(map(str, sorted(groups)))
                primary_group_str = f" (primary is Group 1)" if self.grouped_results and 1 in groups else ""
                print(f"  Group membership: Group(s) {group_str}{primary_group_str}")

            print(f"  Candidates found: {len(candidates)}")
            
            for idx, candidate in enumerate(candidates, 1):
                print(f"\n  Candidate {idx}:")
                print(f"    Search type: {candidate['search_type']}")
                print(f"    Band gap: {candidate['band_gap']:.4f} eV")
                print(f"    Equation: {candidate['equation']}")
                print(f"    Valid range: {candidate['energy_range_str']}")
                print(f"    Quality: R² = {candidate['r_squared']:.4f}, N = {candidate['n_points']} points")
                print(f"    Validation: {candidate['validation_status']}")
        
        # Display group summary
        if not self.grouped_results:
            print("\n⚠ No consistent groups found across columns")
            print("Each column has unique results - consider reviewing data quality or using --range")
            return

        print("\n" + "="*60)
        print("GROUP SUMMARY")
        print("="*60)
        
        for i, group_info in enumerate(self.grouped_results, 1):
            print(f"\nGROUP {i}:")
            print(f"  Score: {group_info['score']:.1f}")
            print(f"  Columns: {group_info['columns']}/{len(self.tauc_columns)}")
            print(f"  Band gap: {group_info['eg_mean']:.4f} ± {group_info['eg_std']:.4f} eV")
            print(f"  Range: {group_info['eg_range']:.4f} eV\n")
            print(f"  Avg R²: {group_info['avg_r2']:.4f}")
            print(f"  Avg slope: {group_info['avg_slope']:.4f}")
            print(f"  Source: {group_info['early_edge_count']} early_edge, {group_info['manual_count']} manual")
            
            # List columns in this group
            columns_in_group = sorted(set(c['column'] for c in group_info['group']))
            print(f"  Members: {', '.join(columns_in_group)}")
        
        # Cross-column comparison table
        print("\n" + "="*60)
        print("CROSS-COLUMN COMPARISON TABLE")
        print("="*60)
        
        # Find primary band gaps for each column
        print(f"\n{'Column':<20} | {'Band Gap(s)':<25} | {'Group(s)':<10} | {'Status'}")
        print("─"*20 + "-+" + "─"*25 + "-+" + "─"*10 + "-+" + "─"*15)
        
        for column in self.tauc_columns:
            if column not in self.column_candidates:
                print(f"{column:<20} | {'N/A':<25} | {'—':<10} | ✗ No results")
                continue
            
            candidates = self.column_candidates[column]
            band_gaps = [f"{c['band_gap']:.3f}" for c in candidates]
            bg_str = ', '.join(band_gaps) + " eV"
            
            groups = self.column_group_map.get(column, [])
            group_str = ", ".join(map(str, sorted(groups))) if groups else "—"
            
            status = "Primary" if (groups and 1 in groups) else "Secondary" if groups else "Ungrouped"
            
            print(f"{column:<20} | {bg_str:<25} | {group_str:<10} | {status}")
        
        # Recommendation
        if len(self.grouped_results) >= 1:
            print("\n" + "="*60)
            print("RECOMMENDATION: Group 1")
            print("="*60)
            best_group = self.grouped_results[0]
            print(f"Primary band gap: {best_group['eg_mean']:.4f} ± {best_group['eg_std']:.4f} eV")
            print(f"Consistency: {best_group['columns']}/{len(self.tauc_columns)} columns")
            
            if any('manual' in c['search_type'] for c in best_group['group']):
                print("Note: This recommendation is based on a user-provided manual search range.")

            if len(self.grouped_results) > 1:
                print(f"\n⚠ Alternative group(s) detected - see above for details")
                
                # Check for anisotropy
                group1_cols = set(c['column'] for c in self.grouped_results[0]['group'])
                group2_cols = set(c['column'] for c in self.grouped_results[1]['group'])
                
                if len(group1_cols) > 0 and len(group2_cols) > 0 and group1_cols != group2_cols:
                    diff_cols = group2_cols - group1_cols
                    if diff_cols:
                        print(f"\n💡 ANISOTROPY DETECTED:")
                        print(f"   Columns {', '.join(sorted(diff_cols))} show different band gap")
                        eg_diff = abs(self.grouped_results[0]['eg_mean'] - self.grouped_results[1]['eg_mean'])
                        print(f"   ΔEg ≈ {eg_diff:.3f} eV")
                        print(f"   This may indicate uniaxial material behavior")
        
        print()
    
    def plot_results(self):
        """Plot results with ALL columns in original file order."""
        if not PLOT_RESULTS or not self.column_candidates:
            if not self.column_candidates: print("⚠ No results to plot")
            return
        
        n_plots = len(self.tauc_columns)
        fig, axes = plt.subplots(n_plots, 1, figsize=(12, 6*n_plots), squeeze=False)
        axes = axes.flatten()

        for i, column in enumerate(self.tauc_columns):
            ax = axes[i]
            
            if column not in self.column_candidates:
                ax.text(0.5, 0.5, f'No results found for {column}', transform=ax.transAxes, ha='center', va='center', fontsize=14, color='red')
                ax.set_title(f'{column} - No Results', fontsize=12, fontweight='bold')
            else:
                candidates = self.column_candidates[column]
                result = candidates[0]
                groups = self.column_group_map.get(column, [])
                group_str = f"Group(s) {', '.join(map(str, sorted(groups)))}" if groups else "Ungrouped"
                
                ax.plot(result['original_energy'], result['original_tauc'], 'o-', color='lightgray', markersize=3, alpha=0.5, label='Original Data')
                ax.plot(result['filtered_energy'], result['filtered_tauc'], 'o-', color='blue', markersize=4, linewidth=1.5, label='Filtered Data')
                
                colors = ['red', 'orange', 'purple', 'green', 'cyan', 'magenta']
                for idx, candidate in enumerate(candidates):
                    color = colors[idx % len(colors)]
                    label_prefix = candidate['search_type'].replace('_', ' ').title()
                    
                    ax.plot(candidate['linear_energy_range'], candidate['linear_tauc_range'], 'o', color=color, markersize=7, label=f'Fit Region ({label_prefix})')
                    
                    energy_ext = np.linspace(candidate['band_gap'], candidate['energy_max'], 100)
                    tauc_ext = candidate['slope'] * energy_ext + candidate['intercept']
                    ax.plot(energy_ext, tauc_ext, '--', color=color, linewidth=2.5, label=f'Fit (R²={candidate["r_squared"]:.4f})')
                    
                    ax.axvline(x=candidate['band_gap'], color=color, linestyle=':', linewidth=3, alpha=0.7, label=f'Eg ({label_prefix}) = {candidate["band_gap"]:.3f} eV')
                
                if result['first_peak'] and result['first_peak'].get('peak_value') is not None:
                    peak = result['first_peak']
                    ax.plot(peak['peak_energy'], peak['peak_value'], 'g*', markersize=15, markeredgecolor='darkgreen', label=f'Peak = {peak["peak_energy"]:.3f} eV')
                
                eg_list = ', '.join([f"{c['band_gap']:.3f}" for c in candidates])
                ax.set_title(f'{column} - Band Gaps: {eg_list} eV [{group_str}]', fontsize=12, fontweight='bold')

                # Add info card for the best candidate (candidates[0])
                if candidates:
                    best_candidate = candidates[0]
                    info_text = (
                        f"Eg = {best_candidate['band_gap']:.3f} eV\n"
                        f"R² = {best_candidate['r_squared']:.4f}\n"
                        f"{best_candidate['equation']}"
                    )
                    ax.text(0.05, 0.5, info_text, transform=ax.transAxes,
                            fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))

            ax.set_xlabel('Energy (eV)', fontsize=11, fontweight='bold')
            ax.set_ylabel('Tauc Function', fontsize=11, fontweight='bold')
            ax.legend(loc='best', fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)

        plt.tight_layout(rect=[0, 0, 1, 0.98])
        fig.suptitle(f'Tauc Analysis for {os.path.basename(self.filename)}', fontsize=16, fontweight='bold')

        if SAVE_PLOTS:
            plot_file = os.path.splitext(self.filename)[0] + '_enhanced_analysis.png'
            plt.savefig(plot_file, dpi=PLOT_DPI, bbox_inches='tight')
            print(f"\n✓ Plot saved: {plot_file}")
        
        if SHOW_PLOTS:
            plt.show()
        else:
            plt.close(fig) # Explicitly close the figure
    
    def save_results(self, output_filename=None):
        """Save results organized by column order."""
        if not self.column_candidates:
            print("⚠ No results to save")
            return
        
        if output_filename is None:
            output_filename = os.path.splitext(self.filename)[0] + '_band_gaps_enhanced.txt'
        
        with open(output_filename, 'w') as f:
            f.write("# Enhanced Adaptive Tauc Plot Band Gap Analysis Results\n")
            f.write(f"# Input: {self.filename}\n")
            f.write(f"# Method: Dual automatic search + optional manual search\n")
            f.write(f"# Search types: near_peak, early_edge, manual_1, manual_2...\n")
            f.write(f"# Grouping tolerance: ±{GROUPING_TOLERANCE} eV\n")
            f.write(f"# Quality: R² ≥ {STRICT_MIN_R_SQUARED}, Points ∈ [{STRICT_MIN_POINTS}, {STRICT_MAX_POINTS}]\n")
            f.write("#\n")
            f.write("# RESULTS ORGANIZED BY COLUMN (Original File Order)\n")
            f.write("#\n")
            
            # Write results for each column in original order
            for column in self.tauc_columns:
                f.write("\n" + "="*70 + "\n") # Fixed f-string for separator
                f.write(f"COLUMN: {column}\n")
                f.write("="*70 + "\n") # Fixed f-string for separator
                
                if column not in self.column_candidates:
                    f.write("# No results found for this column\n")
                    continue
                
                candidates = self.column_candidates[column]
                groups = self.column_group_map.get(column, [])
                
                f.write(f"# Group membership: {groups[0] if groups else 'Ungrouped'}\n")
                f.write(f"# Candidates found: {len(candidates)}\n#\n")
                
                f.write("Search_Type\tBand_Gap(eV)\tEquation\tValid_Range(eV)\t")
                f.write("R²\tSlope\tIntercept\tN_Points\tValidation\n")
                
                for candidate in candidates:
                    f.write(f"{candidate['search_type']}\t")
                    f.write(f"{candidate['band_gap']:.{FLOAT_PRECISION}f}\t")
                    f.write(f"{candidate['equation']}\t")
                    f.write(f"{candidate['energy_range_str']}\t")
                    f.write(f"{candidate['r_squared']:.{FLOAT_PRECISION}f}\t")
                    f.write(f"{candidate['slope']:.{FLOAT_PRECISION}f}\t")
                    f.write(f"{candidate['intercept']:.{FLOAT_PRECISION}f}\t")
                    f.write(f"{candidate['n_points']}\t")
                    f.write(f"{candidate['validation_status']}\n")
            
            # Write group summary
            if self.grouped_results:
                f.write("\n" + "="*70 + "\n") # Fixed f-string for separator
                f.write("GROUP SUMMARY\n")
                f.write("="*70 + "\n\n") # Fixed f-string for separator
                
                for i, group_info in enumerate(self.grouped_results, 1):
                    f.write(f"GROUP {i}:\n")
                    f.write(f"  Score: {group_info['score']:.2f}\n")
                    f.write(f"  Columns: {group_info['columns']}/{len(self.tauc_columns)}\n")
                    f.write(f"  Band gap: {group_info['eg_mean']:.4f} ± {group_info['eg_std']:.4f} eV\n")
                    f.write(f"  Range: {group_info['eg_range']:.4f} eV\n")
                    f.write(f"  Avg R²: {group_info['avg_r2']:.4f}\n")
                    f.write(f"  Avg slope: {group_info['avg_slope']:.4f}\n")
                    f.write(f"  Source: {group_info['early_edge_count']} early_edge, {group_info['manual_count']} manual\n")
                    
                    columns_in_group = sorted(set(c['column'] for c in group_info['group']))
                    f.write(f"  Members: {', '.join(columns_in_group)}\n\n")
            
            # Write cross-column comparison table
            f.write("="*70 + "\n") # Fixed f-string for separator
            f.write("CROSS-COLUMN COMPARISON TABLE\n")
            f.write("="*70 + "\n\n") # Fixed f-string for separator
            f.write("Column\tBand_Gap(s)_eV\tGroup(s)\tStatus\n")
            
            f.write("─"*20 + "-+" + "─"*25 + "-+" + "─"*10 + "-+" + "─"*15 + "\n") # Fixed f-string for separator
            
            for column in self.tauc_columns:
                if column not in self.column_candidates:
                    f.write(f"{column}\tN/A\t—\tNo_results\n")
                    continue
                
                candidates = self.column_candidates[column]
                band_gaps = ', '.join([f"{c['band_gap']:.3f}" for c in candidates])
                
                groups = self.column_group_map.get(column, [])
                group_str = ", ".join(map(str, sorted(groups))) if groups else "—"
                
                status = "Primary" if (groups and 1 in groups) else "Secondary" if groups else "Ungrouped"
                
                f.write(f"{column}\t{band_gaps}\t{group_str}\t{status}\n")
            
            # Write recommendation
            if self.grouped_results:
                f.write("\n" + "="*70 + "\n") # Fixed f-string for separator
                f.write("RECOMMENDATION\n")
                f.write("="*70 + "\n") # Fixed f-string for separator
                f.write(f"Primary group: Group 1\n")
                f.write(f"Band gap: {self.grouped_results[0]['eg_mean']:.4f} ± {self.grouped_results[0]['eg_std']:.4f} eV\n")
                f.write(f"Consistency: {self.grouped_results[0]['columns']}/{len(self.tauc_columns)} columns\n")
                
                if any('manual' in c['search_type'] for c in self.grouped_results[0]['group']):
                    f.write("Note: This recommendation is based on a user-provided manual search range.\n")

                if len(self.grouped_results) > 1:
                    f.write(f"\n⚠ Alternative group(s) detected - see above for details\n") # Added \n
                    
                    # Check for anisotropy
                    group1_cols = set(c['column'] for c in self.grouped_results[0]['group'])
                    group2_cols = set(c['column'] for c in self.grouped_results[1]['group'])
                    
                    if len(group1_cols) > 0 and len(group2_cols) > 0 and group1_cols != group2_cols:
                        diff_cols = group2_cols - group1_cols
                        if diff_cols:
                            f.write(f"\n💡 ANISOTROPY DETECTED:\n")
                            f.write(f"   Columns {', '.join(sorted(diff_cols))} show different band gap\n")
                            eg_diff = abs(self.grouped_results[0]['eg_mean'] - self.grouped_results[1]['eg_mean'])
                            f.write(f"   ΔEg ≈ {eg_diff:.3f} eV\n")
                            f.write(f"   This may indicate uniaxial material behavior\n")
        
        print(f"✓ Results saved: {output_filename}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 4-Slope-Line-Calculation-V14.py input_file.txt [output_file.txt] "
              "[--range start1 end1] [--range start2 end2] [--electronic-gap VALUE]")
        print("  --electronic-gap VALUE : this material/approach's own DFT electronic (band-")
        print("                           structure) gap in eV. When given, both automatic search")
        print("                           windows are anchored on this value instead of a raw-peak-")
        print("                           derived window, and are capped at VALUE + "
              f"{ELECTRONIC_GAP_SEARCH_MARGIN_EV} eV - the recommended way to get a reliable fit")
        print("                           for any material, not just the ones already hand-tuned.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = None
    manual_ranges = []
    electronic_gap = None

    # Use a simple iterator-based parser for optional arguments
    args = sys.argv[2:]
    it = iter(args)
    for arg in it:
        if arg == '--range':
            try:
                start = float(next(it))
                end = float(next(it))
                manual_ranges.append((start, end))
            except (StopIteration, ValueError):
                print("✗ --range must be followed by two numeric values for start and end energy.")
                sys.exit(1)
        elif arg == '--electronic-gap':
            try:
                electronic_gap = float(next(it))
            except (StopIteration, ValueError):
                print("✗ --electronic-gap must be followed by one numeric value (eV).")
                sys.exit(1)
        elif output_file is None:
            # Assume the first non-range, non-gap argument is the output file
            output_file = arg

    if not os.path.exists(input_file):
        print(f"✗ File not found: {input_file}")
        sys.exit(1)

    if electronic_gap is not None:
        print(f"✓ Electronic-gap anchor: {electronic_gap:.4f} eV (search capped at "
              f"{electronic_gap + ELECTRONIC_GAP_SEARCH_MARGIN_EV:.4f} eV)")

    # Pass manual_ranges/electronic_gap to the analyzer
    analyzer = TaucAnalyzer(input_file, manual_ranges=manual_ranges, electronic_gap=electronic_gap)
    analyzer.analyze_all_columns()
    analyzer.plot_results()
    analyzer.save_results(output_file)
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print("\nEnhancements applied:")
    print(f"  ✓ Dual-search strategy: near-peak + early absorption edge")
    print(f"  ✓ Manual override via --range <start> <end> arguments")
    print(f"  ✓ REVISED: Scoring logic prioritizes R² fit quality over peak proximity")
    print(f"  ✓ REVISED: Max points for fits reduced to {STRICT_MAX_POINTS} to improve linearity")
    print(f"  ✓ Cross-column validation and grouping")
    print(f"  ✓ Comparative plotting of all found candidates (auto + manual)")
    print(f"  ✓ Cascading fallback for difficult datasets")
    print("\nReminder: Linear equations valid ONLY in specified energy ranges!")
    print("="*60)


if __name__ == "__main__":
    main()
