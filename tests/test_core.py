"""Tests for autotyper.core module."""

import pytest
from autotyper.core import LAYOUTS, infer_default_layout, parse_override_json


def test_layouts_exist():
    """Test that all expected layouts are available."""
    expected_layouts = {"us", "en-in", "fr-azerty", "ovh"}
    assert set(LAYOUTS.keys()) == expected_layouts


def test_layout_mappings():
    """Test that layouts contain expected key mappings."""
    # Test US layout has basic mappings
    us_layout = LAYOUTS["us"]
    assert "a" in us_layout
    assert "A" in us_layout
    assert " " in us_layout
    assert "\n" in us_layout
    
    # Test French layout has AZERTY mappings
    fr_layout = LAYOUTS["fr-azerty"]
    assert "a" in fr_layout
    assert "q" in fr_layout  # 'a' key produces 'q' in AZERTY


def test_infer_default_layout():
    """Test layout inference."""
    layout = infer_default_layout()
    assert layout in LAYOUTS


def test_parse_override_json():
    """Test JSON override parsing."""
    # Test string format
    overrides = parse_override_json('{"a": "KEY_B+shift"}')
    assert "a" in overrides
    assert overrides["a"] == ("KEY_B", True, False)
    
    # Test object format
    overrides = parse_override_json('{"b": {"key": "KEY_C", "shift": true, "altgr": true}}')
    assert "b" in overrides
    assert overrides["b"] == ("KEY_C", True, True)


def test_parse_override_json_invalid():
    """Test JSON override parsing with invalid input."""
    with pytest.raises(ValueError):
        parse_override_json('{"ab": "KEY_B"}')  # Multi-character key
    
    with pytest.raises(ValueError):
        parse_override_json('{"a": 123}')  # Invalid value type
