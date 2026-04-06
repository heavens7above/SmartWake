from datetime import datetime, timezone, timedelta
from src.modules.alarms import calculate_alarm

def test_calculate_alarm_deadline_before_onset():
    onset = "2024-01-01T23:00:00Z"
    deadline = "2024-01-01T22:00:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: The original deadline since deadline <= onset
    expected_dt = datetime.fromisoformat(deadline).replace(tzinfo=timezone.utc)
    assert result == expected_dt.isoformat()

def test_calculate_alarm_deadline_equal_onset():
    onset = "2024-01-01T23:00:00Z"
    deadline = "2024-01-01T23:00:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: The original deadline since deadline <= onset
    expected_dt = datetime.fromisoformat(deadline).replace(tzinfo=timezone.utc)
    assert result == expected_dt.isoformat()

def test_calculate_alarm_less_than_one_cycle():
    onset = "2024-01-01T23:00:00Z"
    # 89 minutes later, cycle is 90 mins by default
    deadline = "2024-01-02T00:29:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: The original deadline since cycles <= 0
    expected_dt = datetime.fromisoformat(deadline).replace(tzinfo=timezone.utc)
    assert result == expected_dt.isoformat()

def test_calculate_alarm_gap_less_than_15_minutes():
    onset = "2024-01-01T23:00:00Z"
    # 90 mins (1 cycle) + 14 mins gap = 104 mins later
    deadline = "2024-01-02T00:44:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: The original deadline because the gap (14 min) is < 15
    expected_dt = datetime.fromisoformat(deadline).replace(tzinfo=timezone.utc)
    assert result == expected_dt.isoformat()

def test_calculate_alarm_gap_greater_or_equal_to_15_minutes():
    onset = "2024-01-01T23:00:00Z"
    # 90 mins (1 cycle) + 15 mins gap = 105 mins later
    deadline = "2024-01-02T00:45:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: The ideal wake time which is exactly at the end of the last full cycle
    # onset + 90 mins = 2024-01-02T00:30:00Z
    expected_ideal_wake = datetime.fromisoformat("2024-01-02T00:30:00Z").replace(tzinfo=timezone.utc)
    assert result == expected_ideal_wake.isoformat()

def test_calculate_alarm_multiple_cycles_with_gap():
    onset = "2024-01-01T23:00:00Z"
    # 3 cycles (270 mins) + 20 mins gap = 290 mins later
    # 23:00 + 4 hrs 50 mins = 03:50
    deadline = "2024-01-02T03:50:00Z"

    result = calculate_alarm(onset, deadline)

    # Expected: 23:00 + 270 mins (4.5 hrs) = 03:30
    expected_ideal_wake = datetime.fromisoformat("2024-01-02T03:30:00Z").replace(tzinfo=timezone.utc)
    assert result == expected_ideal_wake.isoformat()
