import re

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 63
USERNAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
RESERVED_USERNAMES = frozenset({"admin", "cluster-admin"})


def validate_username(username: str | None) -> str:
  """Return an error message when invalid, otherwise an empty string."""
  if username is None:
    return "Username is required."

  normalized = username.strip()
  if not normalized:
    return "Username cannot be empty."

  if len(normalized) < USERNAME_MIN_LENGTH:
    return f"Username must be at least {USERNAME_MIN_LENGTH} characters."

  if len(normalized) > USERNAME_MAX_LENGTH:
    return f"Username must be at most {USERNAME_MAX_LENGTH} characters."

  if not USERNAME_PATTERN.fullmatch(normalized):
    return (
      "Username must be a valid DNS label "
      "(lowercase letters, numbers, hyphens; cannot start or end with a hyphen)."
    )

  if normalized in RESERVED_USERNAMES:
    return f"Username '{normalized}' is reserved."

  return ""
