"""
The three agents of the PR Code Review Squad.

Each agent has a specialised system prompt. The underlying LLM provider is
chosen per-agent via `squad.toml`; we talk to all providers through the
OpenAI-compatible Chat Completions API, so a single SDK covers Gemini, Grok,
OpenRouter, OpenAI, DeepSeek, Groq, …
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from openai import OpenAI


SECURITY_AUDITOR_PROMPT = """You are a Senior Security Engineer. Your job is to review the provided Git Diff (code changes) and identify any potential security vulnerabilities, unsafe data handling, or exposure of sensitive information.

Do not comment on code style or performance. Focus entirely on answering: "Is this code safe to merge?"

If you find issues, list them clearly with a brief explanation of the risk. If you find no security issues, output exactly: "SECURITY CHECK: PASS"."""


OPTIMIZATION_EXPERT_PROMPT = """You are a Principal Software Engineer obsessed with performance and clean code. Your job is to review the provided Git Diff and identify areas where the code could be more efficient, readable, or maintainable.

Look for:
- Redundant loops or inefficient algorithms
- Violations of DRY (Don't Repeat Yourself) principles
- Poorly named variables or overly complex functions

Provide 1 to 3 highly specific, actionable suggestions. If the code is already optimal, output exactly: "OPTIMIZATION CHECK: PASS"."""


TECH_LEAD_PROMPT = """You are an empathetic and experienced Engineering Team Lead. You are receiving two reports about a recent code change:
1. A Security Report
2. An Optimization Report

Your task is to synthesize these reports into a single, well-formatted Pull Request comment.

Rules:
- Be encouraging and polite (e.g., start with "Great work on this feature!").
- Categorize the feedback clearly using Markdown headings (e.g., 🚨 Security, 💡 Suggestions for Improvement).
- Filter out any conflicting advice.
- If both reports say "PASS", leave a comment saying "Code looks solid, approved from my end! 🚀"
- Output ONLY the Markdown PR comment. Do not wrap it in code fences."""


AGENT_PROMPTS: dict[str, str] = {
    "security_auditor": SECURITY_AUDITOR_PROMPT,
    "optimization_expert": OPTIMIZATION_EXPERT_PROMPT,
    "tech_lead": TECH_LEAD_PROMPT,
}

AGENT_DISPLAY_NAMES: dict[str, str] = {
    "security_auditor": "Security Auditor",
    "optimization_expert": "Optimization Expert",
    "tech_lead": "Tech Lead",
}


@dataclass
class AgentResult:
    name: str
    output: str
    provider: str
    model: str


class LLMAgent:
    """One agent: a system prompt + the OpenAI-compatible client to talk to."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        client: OpenAI,
        model: str,
        provider: str,
        temperature: float = 0.4,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.client = client
        self.model = model
        self.provider = provider
        self.temperature = temperature

    def run(self, user_input: str) -> AgentResult:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=self.temperature,
        )
        text = (response.choices[0].message.content or "").strip()
        return AgentResult(self.name, text, self.provider, self.model)


def build_agent(
    agent_key: str,
    client: OpenAI,
    model: str,
    provider: str,
) -> LLMAgent:
    """Factory: build an LLMAgent from a config key + an already-built client."""
    if agent_key not in AGENT_PROMPTS:
        raise ValueError(f"Unknown agent key: {agent_key!r}")
    return LLMAgent(
        name=AGENT_DISPLAY_NAMES[agent_key],
        system_prompt=AGENT_PROMPTS[agent_key],
        client=client,
        model=model,
        provider=provider,
    )


def synthesize_input(security_report: str, optimization_report: str) -> str:
    return (
        "## Security Report\n"
        f"{security_report}\n\n"
        "## Optimization Report\n"
        f"{optimization_report}\n"
    )


# ---------------------------------------------------------------------------
# Back-compat shims kept so older smoke tests / external callers still work.
# ---------------------------------------------------------------------------


def configure_gemini(_api_key: str) -> None:  # pragma: no cover
    """Deprecated. Provider clients are now built per-agent via providers.py."""
    return None


def build_squad(
    model_name: Optional[str] = None,  # noqa: ARG001
) -> tuple[LLMAgent, LLMAgent, LLMAgent]:  # pragma: no cover
    raise RuntimeError(
        "build_squad() is no longer used directly. cli.py now assembles the "
        "squad from squad.toml via providers.build_client + build_agent."
    )
