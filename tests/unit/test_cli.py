from tools.publishing.__main__ import parser


def test_public_defaults_and_choices() -> None:
    args = parser().parse_args([])
    assert (args.action, args.format, args.profile, args.typography) == ("Build", "pdf", None, None)


def test_all_format_and_thesis_arguments() -> None:
    args = parser().parse_args(["--action", "Build", "--profile", "thesis", "--format", "all"])
    assert args.profile == "thesis"
    assert args.format == "all"
