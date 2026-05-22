"""
The three agents of the PR Code Review Squad.
Each agent has a specialized system prompt and uses Google Gemini for inference
via the official `google-genai` SDK.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types as genai_types


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


_client: Optional[genai.Client] = None


def configure_gemini(api_key: str) -> None:
    """Initialise the module-level Gemini client."""
    global _client
    _client = genai.Client(api_key=api_key)


def _get_client() -> genai.Client:
    if _client is None:
        raise RuntimeError("Gemini client not configured. Call configure_gemini(api_key) first.")
    return _client


@dataclass
class AgentResult:
    name: str
    output: str


class GeminiAgent:
    """Lightweight wrapper around a Gemini model with a fixed system instruction."""

    def __init__(self, name: str, system_prompt: str, model_name: Optional[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def run(self, user_input: str) -> AgentResult:
        client = _get_client()
        response = client.models.generate_content(
            model=self.model_name,
            contents=user_input,
            config=genai_types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.4,
            ),
        )
        text = (response.text or "").strip()
        return AgentResult(name=self.name, output=text)


def build_squad(model_name: Optional[str] = None) -> tuple[GeminiAgent, GeminiAgent, GeminiAgent]:
    security = GeminiAgent("Security Auditor", SECURITY_AUDITOR_PROMPT, model_name)
    optimizer = GeminiAgent("Optimization Expert", OPTIMIZATION_EXPERT_PROMPT, model_name)
    tech_lead = GeminiAgent("Tech Lead", TECH_LEAD_PROMPT, model_name)
    return security, optimizer, tech_lead


def synthesize_input(security_report: str, optimization_report: str) -> str:
    return (
        "## Security Report\n"
        f"{security_report}\n\n"
        "## Optimization Report\n"
        f"{optimization_report}\n"
    )
