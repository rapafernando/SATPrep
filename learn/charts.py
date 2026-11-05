"""Tiny helpers that turn numbers into SVG coordinates (no chart library needed)."""


def line_points(values, width=600, height=200, pad=16, lo=None, hi=None):
    """Return an SVG 'points' string for a line through the values, plus the (x, y) of each point."""
    if not values:
        return "", []
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    if hi == lo:
        hi, lo = hi + 50, lo - 50
    span_x = width - 2 * pad
    span_y = height - 2 * pad
    count = len(values)
    points = []
    for i, value in enumerate(values):
        x = pad + (span_x * i / (count - 1) if count > 1 else span_x / 2)
        y = pad + span_y * (1 - (value - lo) / (hi - lo))
        points.append((round(x, 1), round(y, 1)))
    return " ".join(f"{x},{y}" for x, y in points), points


def bar_heights(counts, max_height=100):
    peak = max(counts) if counts and max(counts) > 0 else 1
    return [round(max_height * c / peak) for c in counts]
