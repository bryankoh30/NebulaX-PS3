"""Feature extraction for Door cycle segments.

Each door-cycle segment (a DataFrame slice from the continuous recording) is
reduced to a fixed-length feature vector.  All features are derived from the
motor signals (current, voltage, back-EMF) and door-position signal, per the
info kit guidance.

The feature order is saved with the model artifact so that future inference
uses the exact same column order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Ordered list of feature names — this order is the contract between training
# and inference.  Never reorder without regenerating the artifact.
FEATURE_NAMES: list[str] = [
    # Duration
    "duration_ms",
    "n_rows",
    # Motor current (mA) statistics
    "current_mean",
    "current_std",
    "current_min",
    "current_max",
    "current_p25",
    "current_p50",
    "current_p75",
    "current_range",
    "current_peak_mean_ratio",  # peak / mean (overcurrent indicator)
    # Motor voltage (10 mV) statistics
    "voltage_mean",
    "voltage_std",
    "voltage_min",
    "voltage_max",
    "voltage_range",
    # Back-EMF statistics
    "bemf_mean",
    "bemf_std",
    "bemf_min",
    "bemf_max",
    "bemf_range",
    # Door leaf position statistics
    "pos_mean",
    "pos_std",
    "pos_min",
    "pos_max",
    "pos_range",
    "pos_start",
    "pos_end",
    "pos_net_change",   # signed: end - start
    # Position monotonicity (fraction of steps in the dominant direction)
    "pos_mono_frac",
    # Power proxy (current * voltage mean)
    "power_mean",
    # Current × time (impulse proxy)
    "current_area",
    # Successive-difference RMS (roughness)
    "current_diff_rms",
    "pos_diff_rms",
]


def extract_features(seg: pd.DataFrame) -> np.ndarray:
    """Compute the feature vector for a single door-cycle segment.

    Parameters
    ----------
    seg:
        A DataFrame slice representing one door cycle.  Must contain the
        standard Door columns including ``ts``.

    Returns
    -------
    np.ndarray
        1-D array of length ``len(FEATURE_NAMES)``.
    """
    cur = seg["Motor current(mA)"].to_numpy(dtype=float)
    vol = seg["Motor Voltage(10mV)"].to_numpy(dtype=float)
    bemf = seg["Motor electrodynamic force"].to_numpy(dtype=float)
    pos = seg["Door leaf position"].to_numpy(dtype=float)

    duration_ms = (seg["ts"].iloc[-1] - seg["ts"].iloc[0]).total_seconds() * 1000.0
    n = len(seg)

    # Current features
    c_mean = float(np.mean(cur))
    c_std = float(np.std(cur, ddof=1)) if n > 1 else 0.0
    c_min = float(np.min(cur))
    c_max = float(np.max(cur))
    c_p25 = float(np.percentile(cur, 25))
    c_p50 = float(np.percentile(cur, 50))
    c_p75 = float(np.percentile(cur, 75))
    c_range = c_max - c_min
    c_peak_mean = c_max / (c_mean + 1e-6)

    # Voltage features
    v_mean = float(np.mean(vol))
    v_std = float(np.std(vol, ddof=1)) if n > 1 else 0.0
    v_min = float(np.min(vol))
    v_max = float(np.max(vol))
    v_range = v_max - v_min

    # Back-EMF features
    b_mean = float(np.mean(bemf))
    b_std = float(np.std(bemf, ddof=1)) if n > 1 else 0.0
    b_min = float(np.min(bemf))
    b_max = float(np.max(bemf))
    b_range = b_max - b_min

    # Position features
    p_mean = float(np.mean(pos))
    p_std = float(np.std(pos, ddof=1)) if n > 1 else 0.0
    p_min = float(np.min(pos))
    p_max = float(np.max(pos))
    p_range = p_max - p_min
    p_start = float(pos[0])
    p_end = float(pos[-1])
    p_net = p_end - p_start

    # Position monotonicity
    if n > 1:
        diffs = np.diff(pos)
        dominant = np.sign(np.sum(diffs))  # +1 opening, -1 closing
        if dominant != 0:
            mono = float(np.sum(np.sign(diffs) == dominant) / len(diffs))
        else:
            mono = 0.0
    else:
        mono = 1.0

    # Power proxy
    power_mean = float(np.mean(cur * vol))

    # Current area (integral proxy using trapezoidal rule over uniform 20ms steps)
    current_area = float(np.trapezoid(cur)) * 20.0  # unit: mA·ms

    # Roughness: successive-difference RMS
    cur_diff_rms = float(np.sqrt(np.mean(np.diff(cur) ** 2))) if n > 1 else 0.0
    pos_diff_rms = float(np.sqrt(np.mean(np.diff(pos) ** 2))) if n > 1 else 0.0

    return np.array([
        duration_ms, float(n),
        c_mean, c_std, c_min, c_max, c_p25, c_p50, c_p75, c_range, c_peak_mean,
        v_mean, v_std, v_min, v_max, v_range,
        b_mean, b_std, b_min, b_max, b_range,
        p_mean, p_std, p_min, p_max, p_range, p_start, p_end, p_net, mono,
        power_mean, current_area,
        cur_diff_rms, pos_diff_rms,
    ], dtype=float)


def build_feature_matrix(
    segments: list[pd.DataFrame],
) -> np.ndarray:
    """Stack feature vectors for a list of segments into a 2-D matrix.

    Returns an (N, len(FEATURE_NAMES)) array.
    """
    if not segments:
        return np.empty((0, len(FEATURE_NAMES)), dtype=float)
    return np.vstack([extract_features(s) for s in segments])
