from pathlib import Path

from tools.publishing import watch as watch_module
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


def test_watch_tracks_unified_sources_without_legacy_manifest(tmp_path: Path) -> None:
    document = tmp_path / "sources/paper"
    document.mkdir(parents=True)
    source = document / "document.yaml"
    source.write_text("title: Paper", encoding="utf-8")
    assert source in watched_files(tmp_path)
    assert watch_module._snapshot(tmp_path)[source] == source.stat().st_mtime_ns


def test_watch_debounces_until_quiet(monkeypatch, tmp_path: Path) -> None:
    clock = [0.0]
    snapshots = iter([{"source": 2}, {"source": 2}, {"source": 2}, {"source": 2}])

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(watch_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(watch_module.time, "sleep", sleep)
    monkeypatch.setattr(watch_module, "_snapshot", lambda *_: next(snapshots))
    result = watch_module.wait_for_quiet(tmp_path, tmp_path / "manifest.yaml", {"source": 1}, quiet_period=0.3)
    assert result == {"source": 2}
    assert clock[0] >= 0.4
