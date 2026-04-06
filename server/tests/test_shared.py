import pytest
from src.modules.shared import cyclical_encode

def test_cyclical_encode():
    # Midnight: 0 minutes. sin(0)=0, cos(0)=1
    sin_val, cos_val = cyclical_encode(0, 0)
    assert sin_val == pytest.approx(0.0, abs=1e-9)
    assert cos_val == pytest.approx(1.0, abs=1e-9)

    # 6 AM: 360 minutes. 360/1440 * 2pi = pi/2. sin(pi/2)=1, cos(pi/2)=0
    sin_val, cos_val = cyclical_encode(6, 0)
    assert sin_val == pytest.approx(1.0, abs=1e-9)
    assert cos_val == pytest.approx(0.0, abs=1e-9)

    # Noon: 720 minutes. 720/1440 * 2pi = pi. sin(pi)=0, cos(pi)=-1
    sin_val, cos_val = cyclical_encode(12, 0)
    assert sin_val == pytest.approx(0.0, abs=1e-9)
    assert cos_val == pytest.approx(-1.0, abs=1e-9)

    # 6 PM: 1080 minutes. 1080/1440 * 2pi = 3pi/2. sin(3pi/2)=-1, cos(3pi/2)=0
    sin_val, cos_val = cyclical_encode(18, 0)
    assert sin_val == pytest.approx(-1.0, abs=1e-9)
    assert cos_val == pytest.approx(0.0, abs=1e-9)
