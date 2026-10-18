from tools.publishing.__main__ import parser
from tools.publishing.options import resolve_options


def test_public_defaults_and_choices() -> None:
    args = parser().parse_args([])
    options = resolve_options(args, {})
    assert (options.action, options.format, options.template, options.typography) == ("Build", "pdf", None, None)


def test_all_format_and_thesis_arguments() -> None:
    args = parser().parse_args(["--action", "Build", "--profile", "thesis", "--format", "all"])
    assert args.profile == "thesis"
    assert args.format == "all"
