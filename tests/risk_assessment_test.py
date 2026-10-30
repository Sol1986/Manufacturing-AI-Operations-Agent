
from old.checkpoint_lab import assess_risk


def test_high_temperature():
    result = assess_risk(
        {
            "machine_id": "M-103",
            "temperature": 85.5,
        }
    )

    assert result["risk_level"] == "high"


def test_normal_temperature():
    result = assess_risk(
        {
            "machine_id": "M-103",
            "temperature": 72.0,
        }
    )

    assert result["risk_level"] == "normal"


def test_boundary_temperature():
    result = assess_risk(
        {
            "machine_id": "M-103",
            "temperature": 80.0,
        }
    )

    assert result["risk_level"] == "high"
