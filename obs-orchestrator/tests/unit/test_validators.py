import pytest

from validators import validate_username


@pytest.mark.parametrize("username", ["abc", "user-1", "a1b", "x" * 63, "  padded  "])
def test_valid_usernames(username):
    assert validate_username(username) == ""


@pytest.mark.parametrize(
    "username, fragment",
    [
        (None, "required"),
        ("", "cannot be empty"),
        ("   ", "cannot be empty"),
        ("ab", "at least 3"),
        ("x" * 64, "at most 63"),
        ("Upper", "valid DNS label"),
        ("-abc", "valid DNS label"),
        ("abc-", "valid DNS label"),
        ("a_b_c", "valid DNS label"),
        ("admin", "reserved"),
        ("cluster-admin", "reserved"),
    ],
)
def test_invalid_usernames(username, fragment):
    assert fragment in validate_username(username)
