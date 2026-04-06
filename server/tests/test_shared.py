import pytest
from src.modules.shared import compute_magnitude

def test_compute_magnitude():
    # Positive values
    assert compute_magnitude(3.0, 4.0, 0.0) == 5.0

    # Negative values
    assert compute_magnitude(-3.0, -4.0, 0.0) == 5.0

    # Mixed values
    assert compute_magnitude(-3.0, 4.0, 0.0) == 5.0

    # Zero vector
    assert compute_magnitude(0.0, 0.0, 0.0) == 0.0

    # 3D vector
    assert compute_magnitude(2.0, 3.0, 6.0) == 7.0
