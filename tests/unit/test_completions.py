"""Tests for shell completion script generation."""

from __future__ import annotations

import pytest

from adversarial_debate.completions import (
    get_completion_script,
    get_install_instructions,
    print_completion_script,
)


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_get_completion_script_returns_non_empty(shell: str) -> None:
    script = get_completion_script(shell)
    assert script
    assert script == script.strip()
    # Every shell completion references the CLI binary name.
    assert "adversarial-debate" in script


def test_bash_script_registers_completion_function() -> None:
    assert "complete -F _adversarial_debate_completions adversarial-debate" in (
        get_completion_script("bash")
    )


def test_zsh_script_has_compdef_header() -> None:
    assert get_completion_script("zsh").startswith("#compdef adversarial-debate")


def test_scripts_cover_all_subcommands() -> None:
    for shell in ("bash", "zsh", "fish"):
        script = get_completion_script(shell)
        for command in ("analyze", "orchestrate", "verdict", "run", "watch", "cache"):
            assert command in script, f"{command} missing from {shell} completion"


def test_get_completion_script_unknown_shell_raises() -> None:
    with pytest.raises(ValueError, match="Unknown shell"):
        get_completion_script("powershell")


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_install_instructions_mention_shell(shell: str) -> None:
    instructions = get_install_instructions(shell)
    assert "adversarial-debate --completions" in instructions


def test_install_instructions_unknown_shell_is_graceful() -> None:
    # Unlike get_completion_script, instructions return a message rather than raise.
    assert "Unknown shell" in get_install_instructions("powershell")


def test_print_completion_script_writes_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    print_completion_script("bash")
    captured = capsys.readouterr()
    assert "_adversarial_debate_completions" in captured.out
