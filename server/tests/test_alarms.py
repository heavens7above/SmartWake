import pytest
from datetime import datetime, timezone
from src.modules.alarms import calculate_alarm

@pytest.mark.parametrize(
    "onset_time, wake_deadline, cycle_minutes, expected_alarm",
    [
        # Deadline <= Onset
        ("2023-10-27T23:00:00Z", "2023-10-27T22:00:00Z", 90, "2023-10-27T22:00:00+00:00"),
        ("2023-10-27T23:00:00Z", "2023-10-27T23:00:00Z", 90, "2023-10-27T23:00:00+00:00"),

        # Total minutes less than one cycle
        ("2023-10-27T23:00:00Z", "2023-10-27T23:30:00Z", 90, "2023-10-27T23:30:00+00:00"),
        ("2023-10-27T23:00:00Z", "2023-10-28T00:29:00Z", 90, "2023-10-28T00:29:00+00:00"),

        # Gap < 15 minutes (should return deadline)
        # Onset: 23:00, Deadline: 02:05 (3h5m = 185m). 2 cycles = 180m. Ideal wake = 02:00. Gap = 5m < 15m.
        ("2023-10-27T23:00:00Z", "2023-10-28T02:05:00Z", 90, "2023-10-28T02:05:00+00:00"),

        # Gap == 14 minutes (should return deadline)
        # Onset: 23:00, Deadline: 02:14 (3h14m = 194m). 2 cycles = 180m. Ideal wake = 02:00. Gap = 14m < 15m.
        ("2023-10-27T23:00:00Z", "2023-10-28T02:14:00Z", 90, "2023-10-28T02:14:00+00:00"),

        # Gap >= 15 minutes (should return ideal wake)
        # Onset: 23:00, Deadline: 02:15 (3h15m = 195m). 2 cycles = 180m. Ideal wake = 02:00. Gap = 15m >= 15m.
        ("2023-10-27T23:00:00Z", "2023-10-28T02:15:00Z", 90, "2023-10-28T02:00:00+00:00"),

        # Gap > 15 minutes (should return ideal wake)
        # Onset: 23:00, Deadline: 02:30 (3h30m = 210m). 2 cycles = 180m. Ideal wake = 02:00. Gap = 30m >= 15m.
        ("2023-10-27T23:00:00Z", "2023-10-28T02:30:00Z", 90, "2023-10-28T02:00:00+00:00"),

        # Custom cycle_minutes
        # Onset: 23:00, Deadline: 01:10 (2h10m = 130m). cycle = 60m. 2 cycles = 120m. Ideal wake = 01:00. Gap = 10m < 15m -> returns deadline
        ("2023-10-27T23:00:00Z", "2023-10-28T01:10:00Z", 60, "2023-10-28T01:10:00+00:00"),

        # Custom cycle_minutes >= 15 gap
        # Onset: 23:00, Deadline: 01:20 (2h20m = 140m). cycle = 60m. 2 cycles = 120m. Ideal wake = 01:00. Gap = 20m >= 15m -> returns ideal wake
        ("2023-10-27T23:00:00Z", "2023-10-28T01:20:00Z", 60, "2023-10-28T01:00:00+00:00"),
    ]
)
def test_calculate_alarm(onset_time, wake_deadline, cycle_minutes, expected_alarm):
    result = calculate_alarm(onset_time, wake_deadline, cycle_minutes)
    assert result == expected_alarm
