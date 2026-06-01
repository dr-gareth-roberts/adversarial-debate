"""Guards on the top-level public API surface.

Regression cover for a real gap where ``CryptoAgent`` existed and was used by
the CLI but was never exported from the package root, so
``from adversarial_debate import CryptoAgent`` raised ImportError.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import adversarial_debate
import adversarial_debate.agents as agents_pkg
from adversarial_debate.agents.base import Agent


def _concrete_agent_classes() -> set[str]:
    found: set[str] = set()
    for module_info in pkgutil.iter_modules(agents_pkg.__path__):
        module = importlib.import_module(f"adversarial_debate.agents.{module_info.name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Agent)
                and obj is not Agent
                and obj.__module__.startswith("adversarial_debate.agents")
            ):
                found.add(name)
    return found


def test_all_concrete_agents_are_exported_from_package_root() -> None:
    missing = sorted(
        name for name in _concrete_agent_classes() if not hasattr(adversarial_debate, name)
    )
    assert not missing, f"agent classes missing from top-level package: {missing}"


def test_crypto_agent_is_importable_from_root() -> None:
    from adversarial_debate import CryptoAgent

    assert CryptoAgent.__name__ == "CryptoAgent"


def test_all_dunder_matches_real_attributes() -> None:
    # Everything advertised in __all__ must actually resolve.
    missing = [name for name in adversarial_debate.__all__ if not hasattr(adversarial_debate, name)]
    assert not missing, f"names in __all__ with no attribute: {missing}"
