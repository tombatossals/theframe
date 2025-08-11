import pytest
from pathlib import Path
import json
import os

from tools import get_incremental_pending_name, get_incremental_completed_name


def test_get_incremental_pending_name() -> None:
    """Test that get_incremental_pending_name returns the correct filename."""
    test_path = "/tmp/test.json"
    expected = "/tmp/test.incremental.pending.json"
    assert get_incremental_pending_name(test_path) == expected


def test_get_incremental_completed_name() -> None:
    """Test that get_incremental_completed_name returns the correct filename."""
    test_path = "/tmp/test.json"
    expected = "/tmp/test.incremental.completed.json"
    assert get_incremental_completed_name(test_path) == expected


def test_get_incremental_names_with_subdirectories() -> None:
    """Test that the functions work with subdirectories."""
    test_path = "/tmp/data/test.json"
    expected_pending = "/tmp/data/test.incremental.pending.json"
    expected_completed = "/tmp/data/test.incremental.completed.json"

    assert get_incremental_pending_name(test_path) == expected_pending
    assert get_incremental_completed_name(test_path) == expected_completed


def test_get_incremental_names_invalid_extension() -> None:
    """Test that the functions raise ValueError for non-JSON files."""
    test_path = "/tmp/test.txt"

    with pytest.raises(ValueError, match="File must end in .json"):
        get_incremental_pending_name(test_path)

    with pytest.raises(ValueError, match="File must end in .json"):
        get_incremental_completed_name(test_path)
