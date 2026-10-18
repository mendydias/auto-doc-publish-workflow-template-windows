from pathlib import Path

from tools.publishing.watch import watched_files


def test_watch_excludes_outputs_and_cache(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "a.md").touch()
    build = tmp_path / "build"
    build.mkdir()
    (build / "generated.md").touch()
    manifest = tmp_path / "config/documents/example.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.touch()
    paths = watched_files(tmp_path, manifest)
    assert manifest in paths and sources / "a.md" in paths
    assert all("build" not in path.parts for path in paths)
