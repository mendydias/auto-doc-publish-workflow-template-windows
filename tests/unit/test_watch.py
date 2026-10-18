from pathlib import Path

from tools.publishing import watch as watch_module
from tools.publishing.watch import watched_files


def test_watch_tracks_selected_document_and_shared_inputs_only(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    document = sources / "paper"
    document.mkdir(parents=True)
    source = document / "document.yaml"
    source.touch()
    other = sources / "other"
    other.mkdir()
    (other / "document.yaml").touch()
    build = tmp_path / "build"
    build.mkdir()
    (build / "generated.md").touch()
    shared = tmp_path / "config/profiles/article.yaml"
    shared.parent.mkdir(parents=True)
    shared.touch()
    paths = watched_files(tmp_path, "paper")
    assert source in paths and shared in paths
    assert all("other" not in path.parts for path in paths)
    assert all("build" not in path.parts for path in paths)


def test_watch_tracks_unified_sources_without_legacy_manifest(tmp_path: Path) -> None:
    document = tmp_path / "sources/paper"
    document.mkdir(parents=True)
    source = document / "document.yaml"
    source.write_text("title: Paper", encoding="utf-8")
    assert source in watched_files(tmp_path)
    assert watch_module._snapshot(tmp_path)[source] == (source.stat().st_mtime_ns, source.stat().st_size)


def test_watch_debounces_until_quiet(monkeypatch, tmp_path: Path) -> None:
    clock = [0.0]
    snapshots = iter([{"source": (2, 1)}, {"source": (2, 1)}, {"source": (2, 1)}, {"source": (2, 1)}])

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(watch_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(watch_module.time, "sleep", sleep)
    monkeypatch.setattr(watch_module, "_snapshot", lambda *_: next(snapshots))
    result = watch_module.wait_for_quiet(tmp_path, "paper", {"source": (1, 1)}, quiet_period=0.3)
    assert result == {"source": (2, 1)}
    assert clock[0] >= 0.4
