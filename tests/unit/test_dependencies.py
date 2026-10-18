from pathlib import Path

from tools.publishing import dependencies


def test_html_dependency_check_does_not_require_tex(monkeypatch, capsys, tmp_path: Path) -> None:
    observed = []

    def fake_run(name, args):
        observed.append(name)
        if name == "pandoc":
            return 0, "pandoc 3.12.1"
        if name == "pandoc-crossref":
            return 0, "pandoc-crossref built with Pandoc v3.12.1"
        return 0, f"{name} version 1.0"

    monkeypatch.setattr(dependencies, "_run", fake_run)
    assert dependencies.check_dependencies(tmp_path, "html") == 0
    assert "lualatex" not in observed
    assert "latexmk" not in observed
    assert "kpsewhich" not in observed


def test_format_all_expands_formats(monkeypatch, tmp_path: Path) -> None:
    observed = []
    def fake_run(name, args):
        observed.append(name)
        version = "pandoc 3.12.1" if name == "pandoc" else "pandoc-crossref built with Pandoc v3.12.1" if name == "pandoc-crossref" else f"{name} 1.0"
        return 0, version

    monkeypatch.setattr(dependencies, "_run", fake_run)
    dependencies.check_dependencies(tmp_path, "all")
    assert {"pandoc", "pandoc-crossref", "lualatex", "latexmk", "kpsewhich"} <= set(observed)


def test_missing_executable_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(dependencies.shutil, "which", lambda _name: None)
    code, message = dependencies._run("missing-native-tool", ["--version"])
    assert code == 127
    assert "not found" in message


def test_native_failure_exit_code_is_preserved(monkeypatch) -> None:
    from tools.publishing import build as build_module
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(build_module, "check_dependencies", lambda *_: 0)
    monkeypatch.setattr(build_module, "validate", lambda *_: [])
    monkeypatch.setattr(build_module, "_command", lambda *_: 42)
    assert build_module.build(root, "example", "article", "default", "html") == 42
