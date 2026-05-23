"""
Provider catalog + squad-config loader.

Every supported provider speaks the OpenAI Chat Completions API; we only need to
swap `base_url` + `api_key` to talk to any of them. This file knows where each
provider lives, which env var holds its key, and where to sign up for one.

The squad's per-agent provider/model assignment lives in `squad.toml` next to
this module. Edit that file to mix providers — no code changes required.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

from openai import OpenAI


# ---------------------------------------------------------------------------
# Provider catalog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    api_key_env: str
    signup_url: str
    notes: str = ""
    default_fast_model: str = ""
    default_best_model: str = ""
    known_models: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelValidationIssue:
    level: str
    agent: str
    provider: str
    model: str
    message: str


MODEL_ALIASES = {
    "default": "default_fast_model",
    "default-fast": "default_fast_model",
    "default-best": "default_best_model",
}


KNOWN_PROVIDERS: dict[str, ProviderSpec] = {
    "gemini": ProviderSpec(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        signup_url="https://aistudio.google.com/apikey",
        notes="Free tier on gemini-2.0-flash",
        default_fast_model="gemini-2.0-flash",
        default_best_model="gemini-2.5-flash",
        known_models=("gemini-2.0-flash", "gemini-2.5-flash"),
    ),
    "grok": ProviderSpec(
        name="grok",
        base_url="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        signup_url="https://console.x.ai/",
        notes="xAI Grok models (grok-2, grok-2-latest, grok-3)",
        default_fast_model="grok-2-latest",
        default_best_model="grok-3",
        known_models=("grok-2", "grok-2-latest", "grok-3"),
    ),
    "openrouter": ProviderSpec(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        signup_url="https://openrouter.ai/keys",
        notes="Aggregator: Claude, GPT, Llama, Mistral, free-tier models, …",
        default_fast_model="anthropic/claude-3.5-haiku",
        default_best_model="meta-llama/llama-3.3-70b-instruct",
        known_models=(
            "anthropic/claude-3.5-haiku",
            "meta-llama/llama-3.3-70b-instruct",
        ),
    ),
    "openai": ProviderSpec(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        signup_url="https://platform.openai.com/api-keys",
        notes="GPT-4o, GPT-4o-mini, o1, …",
        default_fast_model="gpt-4o-mini",
        default_best_model="gpt-4o",
        known_models=("gpt-4o-mini", "gpt-4o"),
    ),
    "deepseek": ProviderSpec(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        signup_url="https://platform.deepseek.com/api_keys",
        notes="deepseek-chat, deepseek-reasoner",
        default_fast_model="deepseek-chat",
        default_best_model="deepseek-reasoner",
        known_models=("deepseek-chat", "deepseek-reasoner"),
    ),
    "groq": ProviderSpec(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        signup_url="https://console.groq.com/keys",
        notes="Ultra-fast inference (llama, mixtral, …)",
        default_fast_model="llama-3.1-8b-instant",
        default_best_model="llama-3.3-70b-versatile",
        known_models=(
            "allam-2-7b",
            "groq/compound",
            "groq/compound-mini",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-safeguard-20b",
            "qwen/qwen3-32b",
        ),
    ),
}


AGENT_KEYS = ("security_auditor", "optimization_expert", "tech_lead")


# Default: Groq-only profile. Works with just GROQ_API_KEY in .env.
DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "security_auditor": {"provider": "groq", "model": "default-fast"},
    "optimization_expert": {"provider": "groq", "model": "default-fast"},
    "tech_lead": {"provider": "groq", "model": "default-best"},
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SquadConfigError(Exception):
    """Anything wrong with squad.toml."""


class MissingKeyError(Exception):
    def __init__(self, spec: ProviderSpec):
        self.spec = spec
        super().__init__(
            f"Missing {spec.api_key_env} for provider '{spec.name}'. "
            f"Get one at {spec.signup_url} and add it to .env."
        )


# ---------------------------------------------------------------------------
# Config loading + client building
# ---------------------------------------------------------------------------


def load_squad_config(path: Optional[Path]) -> dict[str, dict[str, str]]:
    """Load squad.toml; return DEFAULT_CONFIG if file is absent."""
    if path is None or not path.exists():
        return {k: dict(v) for k, v in DEFAULT_CONFIG.items()}

    with open(path, "rb") as f:
        data = tomllib.load(f)

    for agent in AGENT_KEYS:
        if agent not in data:
            raise SquadConfigError(
                f"{path.name} is missing required section [{agent}]"
            )
        section = data[agent]
        if "provider" not in section or "model" not in section:
            raise SquadConfigError(
                f"[{agent}] in {path.name} must set both 'provider' and 'model'"
            )
        if section["provider"] not in KNOWN_PROVIDERS:
            known = ", ".join(sorted(KNOWN_PROVIDERS))
            raise SquadConfigError(
                f"[{agent}] uses unknown provider '{section['provider']}'. "
                f"Supported: {known}"
            )

    return {agent: dict(data[agent]) for agent in AGENT_KEYS}


def resolve_model_alias(provider_name: str, model_name: str) -> str:
    alias_key = model_name.strip()
    alias_attr = MODEL_ALIASES.get(alias_key)
    if not alias_attr:
        return alias_key
    spec = KNOWN_PROVIDERS[provider_name]
    resolved = getattr(spec, alias_attr)
    return resolved or alias_key


def resolve_config_models(config: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    resolved: dict[str, dict[str, str]] = {}
    for agent, cfg in config.items():
        provider_name = cfg["provider"]
        resolved[agent] = {
            "provider": provider_name,
            "model": resolve_model_alias(provider_name, cfg["model"]),
        }
    return resolved


def validate_model_selection(
    config: dict[str, dict[str, str]],
) -> list[ModelValidationIssue]:
    issues: list[ModelValidationIssue] = []
    for agent, cfg in config.items():
        provider_name = cfg["provider"]
        model_name = cfg["model"]
        spec = KNOWN_PROVIDERS[provider_name]
        if model_name in spec.known_models:
            continue

        other_matches = [
            other.name
            for other in KNOWN_PROVIDERS.values()
            if other.name != provider_name and model_name in other.known_models
        ]
        if other_matches:
            issues.append(
                ModelValidationIssue(
                    level="error",
                    agent=agent,
                    provider=provider_name,
                    model=model_name,
                    message=(
                        f"{model_name!r} is not a known-good model for provider "
                        f"{provider_name!r}; it matches {', '.join(other_matches)}."
                    ),
                )
            )
            continue

        issues.append(
            ModelValidationIssue(
                level="warning",
                agent=agent,
                provider=provider_name,
                model=model_name,
                message=(
                    f"{model_name!r} is not in the built-in known-good list for "
                    f"provider {provider_name!r}. Custom model IDs may still work."
                ),
            )
        )
    return issues


def build_client(provider_name: str) -> OpenAI:
    """Return an OpenAI client wired up for the given provider."""
    spec = KNOWN_PROVIDERS[provider_name]
    key = os.environ.get(spec.api_key_env, "").strip()
    if not key or key.startswith("your_"):
        raise MissingKeyError(spec)

    kwargs: dict[str, Any] = {"api_key": key, "base_url": spec.base_url}

    # OpenRouter recommends an identifying header so your traffic is attributed.
    if provider_name == "openrouter":
        kwargs["default_headers"] = {
            "HTTP-Referer": "https://github.com/MadhushanAndawaththa/RoundTable-Ai",
            "X-Title": "RoundTable AI",
        }

    return OpenAI(**kwargs)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def find_default_config(here: Path) -> Optional[Path]:
    """Look for squad.toml next to this module."""
    candidate = here / "squad.toml"
    return candidate if candidate.exists() else None


def validate_keys_for_config(config: dict[str, dict[str, str]]) -> list[ProviderSpec]:
    """Return a list of providers in use whose API keys are missing."""
    needed = {cfg["provider"] for cfg in config.values()}
    missing: list[ProviderSpec] = []
    for provider in needed:
        spec = KNOWN_PROVIDERS[provider]
        key = os.environ.get(spec.api_key_env, "").strip()
        if not key or key.startswith("your_"):
            missing.append(spec)
    return missing


if __name__ == "__main__":  # pragma: no cover - tiny CLI for debugging
    cfg = load_squad_config(find_default_config(Path(__file__).resolve().parent))
    for name, cfg_entry in cfg.items():
        print(f"{name}: {cfg_entry['provider']} · {cfg_entry['model']}")
    missing = validate_keys_for_config(cfg)
    if missing:
        print("\nMissing keys:", ", ".join(s.api_key_env for s in missing), file=sys.stderr)
