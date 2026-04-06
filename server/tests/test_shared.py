import pytest
import math
from src.modules.shared import compute_magnitude

def test_compute_magnitude_zero():
    assert compute_magnitude(0.0, 0.0, 0.0) == 0.0

def test_compute_magnitude_positive():
    assert compute_magnitude(3.0, 4.0, 0.0) == 5.0

def test_compute_magnitude_negative():
    assert compute_magnitude(-3.0, -4.0, 0.0) == 5.0

def test_compute_magnitude_mixed():
    assert compute_magnitude(1.0, -2.0, 2.0) == 3.0

def test_compute_magnitude_decimals():
    assert math.isclose(compute_magnitude(1.5, 2.5, 3.5), 4.55521678957, rel_tol=1e-9)
