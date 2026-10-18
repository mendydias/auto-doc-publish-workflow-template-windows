from pathlib import Path

import pytest

from tools.publishing.clean import clean


def test_clean_removes_only_generated_children(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    (build / ".gitkeep").touch()
    (build / "generated.log").write_text("log")
    (build / "publication").mkdir()
    (build / "publication" / "book.pdf").write_text("pdf")
    assert clean(tmp_path) == 0
    assert (build / ".gitkeep").exists()
    assert list(build.iterdir()) == [build / ".gitkeep"]


def test_clean_refuses_symlink(tmp_path: Path) -> None:
    build = tmp_path / "build"
    outside = tmp_path / "outside"
    build.mkdir()
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (build / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="link/junction"):
        clean(tmp_path)
    assert (outside / "keep.txt").read_text() == "keep"


def test_clean_rejects_build_root_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "build").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe cleanup"):
        clean(tmp_path)
