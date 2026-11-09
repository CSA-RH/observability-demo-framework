from utils import JSONUtils


def test_save_and_load_roundtrip_creates_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "data.json"
    JSONUtils.save_json_to_file({"a": [1, 2]}, str(path))
    assert JSONUtils.load_json_from_file(str(path)) == {"a": [1, 2]}


def test_load_missing_file_returns_empty_list(tmp_path):
    assert JSONUtils.load_json_from_file(str(tmp_path / "missing.json")) == []


def test_load_corrupt_file_returns_none(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("{not json")
    assert JSONUtils.load_json_from_file(str(path)) is None


def test_delete_file_is_idempotent(tmp_path):
    path = tmp_path / "data.json"
    JSONUtils.save_json_to_file([], str(path))
    JSONUtils.delete_json_file(str(path))
    JSONUtils.delete_json_file(str(path))
    assert not path.exists()
