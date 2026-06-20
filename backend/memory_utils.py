"""Process memory tracking for peak RSS and efficiency metrics."""
import os

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

_peak_rss_mb = 0.0


def current_rss_mb():
    if psutil is None:
        return 0.0
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def peak_rss_mb():
    return _peak_rss_mb


def log_memory_usage(label=""):
    global _peak_rss_mb
    rss = current_rss_mb()
    if rss > _peak_rss_mb:
        _peak_rss_mb = rss
    tag = f"[{label}] " if label else ""
    return {"label": label, "rss_mb": round(rss, 1), "peak_rss_mb": round(_peak_rss_mb, 1)}


def reset_peak_rss():
    global _peak_rss_mb
    _peak_rss_mb = current_rss_mb()
    return _peak_rss_mb


def memory_summary():
    return {
        "rss_mb": round(current_rss_mb(), 1),
        "peak_rss_mb": round(peak_rss_mb(), 1),
        "budget_mb": 7168,
        "headroom_mb": round(7168 - peak_rss_mb(), 1),
    }
