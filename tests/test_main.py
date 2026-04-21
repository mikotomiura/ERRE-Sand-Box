"""CLI wiring tests for :mod:`erre_sandbox.__main__`.

These stay argparse-only: no :func:`asyncio.run` is invoked. The
``bootstrap`` coroutine is exercised separately in ``test_bootstrap.py``
and by G-GEAR live evidence runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from erre_sandbox import __main__ as main_mod
from erre_sandbox.__main__ import _build_parser, _resolve_agents
from erre_sandbox.schemas import AgentSpec, Zone

# ---------------------------------------------------------------------------
# --personas expansion
# ---------------------------------------------------------------------------


def test_resolve_agents_returns_empty_when_flag_absent() -> None:
    assert _resolve_agents(None, Path("personas")) == ()


def test_resolve_agents_returns_empty_when_flag_blank() -> None:
    assert _resolve_agents("   ", Path("personas")) == ()
    assert _resolve_agents(",,", Path("personas")) == ()


def test_resolve_agents_expands_kant_nietzsche_rikyu() -> None:
    specs = _resolve_agents("kant,nietzsche,rikyu", Path("personas"))
    assert len(specs) == 3
    assert [s.persona_id for s in specs] == ["kant", "nietzsche", "rikyu"]
    # Each spec's initial_zone is the persona's first preferred_zone.
    assert all(isinstance(s, AgentSpec) for s in specs)
    assert all(isinstance(s.initial_zone, Zone) for s in specs)


def test_resolve_agents_raises_system_exit_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="unknown_persona"):
        _resolve_agents("unknown_persona", tmp_path)


@pytest.mark.parametrize(
    "hostile",
    [
        "../etc/passwd",
        "/etc/passwd",
        "kant/../nietzsche",
        "Kant",  # uppercase rejected
        "_leading",  # must start with a letter
        "x" * 65,  # length cap
    ],
)
def test_resolve_agents_rejects_path_traversal_tokens(
    hostile: str,
    tmp_path: Path,
) -> None:
    """Defence in depth: CLI must reject any persona_id that could escape."""
    with pytest.raises(SystemExit, match="must match"):
        _resolve_agents(hostile, tmp_path)


def test_resolve_agents_strips_whitespace() -> None:
    specs = _resolve_agents(" kant , nietzsche ", Path("personas"))
    assert [s.persona_id for s in specs] == ["kant", "nietzsche"]


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


def test_parser_personas_flag_defaults_to_none() -> None:
    args = _build_parser().parse_args([])
    assert args.personas is None
    assert args.personas_dir == "personas"


def test_parser_personas_flag_accepts_csv() -> None:
    args = _build_parser().parse_args(["--personas", "kant,nietzsche"])
    assert args.personas == "kant,nietzsche"


def test_parser_personas_dir_override(tmp_path: Path) -> None:
    target = str(tmp_path / "custom-personas")
    args = _build_parser().parse_args(["--personas-dir", target])
    assert args.personas_dir == target


# ---------------------------------------------------------------------------
# M5 rollback flags — --disable-erre-fsm / --disable-dialog-turn /
# --disable-mode-sampling. All three default to "enabled" (True); passing
# --disable-* flips the corresponding ``enable_*`` argparse field to False.
# ---------------------------------------------------------------------------


def test_parser_m5_rollback_flags_default_to_enabled() -> None:
    args = _build_parser().parse_args([])
    assert args.enable_erre_fsm is True
    assert args.enable_dialog_turn is True
    assert args.enable_mode_sampling is True


def test_parser_disable_erre_fsm_flips_only_fsm_flag() -> None:
    args = _build_parser().parse_args(["--disable-erre-fsm"])
    assert args.enable_erre_fsm is False
    assert args.enable_dialog_turn is True
    assert args.enable_mode_sampling is True


def test_parser_disable_dialog_turn_flips_only_dialog_flag() -> None:
    args = _build_parser().parse_args(["--disable-dialog-turn"])
    assert args.enable_erre_fsm is True
    assert args.enable_dialog_turn is False
    assert args.enable_mode_sampling is True


def test_parser_disable_mode_sampling_flips_only_sampling_flag() -> None:
    args = _build_parser().parse_args(["--disable-mode-sampling"])
    assert args.enable_erre_fsm is True
    assert args.enable_dialog_turn is True
    assert args.enable_mode_sampling is False


def test_parser_all_three_disable_flags_combine() -> None:
    args = _build_parser().parse_args(
        ["--disable-erre-fsm", "--disable-dialog-turn", "--disable-mode-sampling"],
    )
    assert args.enable_erre_fsm is False
    assert args.enable_dialog_turn is False
    assert args.enable_mode_sampling is False


# ---------------------------------------------------------------------------
# cli() flag propagation smoke — verifies the argparse → bootstrap() kwargs
# wiring so a missed keyword does not silently downgrade to defaults.
# ---------------------------------------------------------------------------


def test_cli_propagates_rollback_flags_to_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``cli()`` must pass the three rollback flags into ``bootstrap()``.

    This catches the silent-no-op class of bugs flagged by the
    impact-analyzer: if ``cli`` forgets to forward a flag, the argparse
    test above still passes but the runtime falls back to defaults
    (all-enabled) and the flag has no effect.
    """
    captured: dict[str, object] = {}

    async def _recording_bootstrap(
        cfg: object,
        *,
        enable_erre_fsm: bool,
        enable_dialog_turn: bool,
        enable_mode_sampling: bool,
    ) -> None:
        captured["cfg"] = cfg
        captured["enable_erre_fsm"] = enable_erre_fsm
        captured["enable_dialog_turn"] = enable_dialog_turn
        captured["enable_mode_sampling"] = enable_mode_sampling

    monkeypatch.setattr(main_mod, "bootstrap", _recording_bootstrap)

    exit_code = main_mod.cli(
        ["--disable-erre-fsm", "--disable-mode-sampling", "--skip-health-check"],
    )
    assert exit_code == 0
    assert captured["enable_erre_fsm"] is False
    assert captured["enable_dialog_turn"] is True  # not disabled
    assert captured["enable_mode_sampling"] is False


def test_cli_defaults_all_rollback_flags_to_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _recording_bootstrap(
        cfg: object,
        *,
        enable_erre_fsm: bool,
        enable_dialog_turn: bool,
        enable_mode_sampling: bool,
    ) -> None:
        captured["enable_erre_fsm"] = enable_erre_fsm
        captured["enable_dialog_turn"] = enable_dialog_turn
        captured["enable_mode_sampling"] = enable_mode_sampling
        _ = cfg

    monkeypatch.setattr(main_mod, "bootstrap", _recording_bootstrap)

    assert main_mod.cli(["--skip-health-check"]) == 0
    assert captured["enable_erre_fsm"] is True
    assert captured["enable_dialog_turn"] is True
    assert captured["enable_mode_sampling"] is True
