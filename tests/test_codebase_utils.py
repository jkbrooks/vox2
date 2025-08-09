from pathlib import Path

from executive_worker.codebase_utils import CodebaseUtilities


def test_codebase_search_python_fallback(tmp_path):
    root = Path(tmp_path)
    (root / "a").mkdir()
    (root / "a" / "file1.txt").write_text("hello world\nfoo bar\n", encoding="utf-8")
    (root / "file2.txt").write_text("no match here\n", encoding="utf-8")

    utils = CodebaseUtilities(str(root))
    hits = utils.search("hello", path_glob="**/*.txt", before=1, after=1)
    assert any("file1.txt" in h.file_path for h in hits)
    assert all(isinstance(h.line_number, int) for h in hits)

