from types import SimpleNamespace

import pytest

from tools.publishing.options import resolve_options


def test_cli_overrides_environment_and_environment_overrides_defaults() -> None:
    args = SimpleNamespace(document="cli", template=None, profile=None, format=None, action=None,
                           typography=None, venue=None, non_interactive=None)
    env = {"PUBLISH_DOCUMENT": "env", "PUBLISH_FORMAT": "html", "PUBLISH_TEMPLATE": "report"}
    options = resolve_options(args, env)
    assert (options.document, options.template, options.format) == ("cli", "report", "html")


def test_conflicting_profile_alias_is_rejected() -> None:
    args = SimpleNamespace(document=None, template="article", profile="thesis", format=None,
                           action=None, typography=None, venue=None, non_interactive=None)
    with pytest.raises(ValueError, match="conflict"):
        resolve_options(args, {})


def test_cli_profile_overrides_environment_template() -> None:
    args = SimpleNamespace(document=None, template=None, profile="report", format=None,
                           action=None, typography=None, venue=None, non_interactive=None)
    assert resolve_options(args, {"PUBLISH_TEMPLATE": "article"}).template == "report"


@pytest.mark.parametrize("env,key", [({"PUBLISH_FORMAT": "unknown"}, "format"),
                                      ({"PUBLISH_ACTION": "prompt"}, "action"),
                                      ({"PUBLISH_DOCUMENT": "../bad"}, "document")])
def test_environment_values_are_validated(env: dict[str, str], key: str) -> None:
    args = SimpleNamespace(document=None, template=None, profile=None, format=None, action=None,
                           typography=None, venue=None, non_interactive=None)
    with pytest.raises(ValueError, match=key):
        resolve_options(args, env)
