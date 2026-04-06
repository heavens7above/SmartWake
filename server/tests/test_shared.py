import math

import pytest

from src.modules.shared import compute_magnitude, cyclical_encode


def test_cyclical_encode():
    sin_val, cos_val = cyclical_encode(0, 0)
    assert sin_val == pytest.approx(0.0, abs=1e-9)
    assert cos_val == pytest.approx(1.0, abs=1e-9)

    sin_val, cos_val = cyclical_encode(6, 0)
    assert sin_val == pytest.approx(1.0, abs=1e-9)
    assert cos_val == pytest.approx(0.0, abs=1e-9)

    sin_val, cos_val = cyclical_encode(12, 0)
    assert sin_val == pytest.approx(0.0, abs=1e-9)
    assert cos_val == pytest.approx(-1.0, abs=1e-9)

    sin_val, cos_val = cyclical_encode(18, 0)
    assert sin_val == pytest.approx(-1.0, abs=1e-9)
    assert cos_val == pytest.approx(0.0, abs=1e-9)


def test_compute_magnitude_positive():
    assert compute_magnitude(3.0, 4.0, 0.0) == 5.0
    assert compute_magnitude(1.0, 2.0, 2.0) == 3.0


def test_compute_magnitude_negative():
    assert compute_magnitude(-3.0, -4.0, 0.0) == 5.0
    assert compute_magnitude(-1.0, -2.0, -2.0) == 3.0


def test_compute_magnitude_mixed():
    assert compute_magnitude(-3.0, 4.0, 0.0) == 5.0
    assert compute_magnitude(1.0, -2.0, 2.0) == 3.0


def test_compute_magnitude_zero_vector():
    assert compute_magnitude(0.0, 0.0, 0.0) == 0.0


def test_compute_magnitude_floats():
    assert math.isclose(
        compute_magnitude(1.1, 2.2, 3.3),
        4.115823125451335,
        rel_tol=1e-9,
    )
