from pathlib import Path

from tools.publishing import dependencies


def test_html_dependency_check_does_not_require_tex(monkeypatch, capsys, tmp_path: Path) -> None:
    observed = []

    def fake_run(name, args):
        observed.append(name)
        return 0, f"{name} version 1.0"

    monkeypatch.setattr(dependencies, "_run", fake_run)
    assert dependencies.check_dependencies(tmp_path, "html") == 0
    assert "lualatex" not in observed
    assert "latexmk" not in observed
    assert "kpsewhich" not in observed


def test_format_all_expands_formats(monkeypatch, tmp_path: Path) -> None:
    observed = []
    monkeypatch.setattr(dependencies, "_run", lambda name, args: (observed.append(name) or 0, f"{name} 1.0"))
    dependencies.check_dependencies(tmp_path, "all")
    assert {"pandoc", "pandoc-crossref", "lualatex", "latexmk", "kpsewhich"} <= set(observed)
