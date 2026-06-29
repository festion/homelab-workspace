"""Unconditional secret redaction over transcript excerpts (stage-1 guardrail).

Every excerpt is run through ``redact`` before it leaves the pre-filter, so no
secret can travel transcript -> candidate -> Vikunja card.
"""
import re

_PATTERNS = [
    re.compile(r"\b(sk-[a-zA-Z0-9_-]{8,})"),                                  # OpenAI/Anthropic-style keys
    re.compile(r"\b(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)"),  # JWT
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,})"),                            # GitHub tokens
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*\S+"),      # key=value
]


def redact(s):
    for p in _PATTERNS:
        s = p.sub("[REDACTED]", s)
    return s
