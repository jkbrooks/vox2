from __future__ import annotations

import pytest

from executive_worker.edit_engine import EditEngine, FileEdit


def test_edit_engine_apply_and_rollback(tmp_path):
    root = tmp_path
    src = root / "a.txt"
    src.write_text("hello world", encoding="utf-8")

    ee = EditEngine(str(root))
    ee.apply_edits([FileEdit(path="a.txt", original_substring="hello", replacement="hey")])

    assert src.read_text(encoding="utf-8").startswith("hey")

    # Now force a failure to trigger rollback
    src.write_text("alpha beta", encoding="utf-8")
    with pytest.raises(RuntimeError):
        ee.apply_edits([FileEdit(path="a.txt", original_substring="gamma", replacement="delta")])
    assert src.read_text(encoding="utf-8") == "alpha beta"
