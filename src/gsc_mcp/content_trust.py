"""Observe narrow FR/EN instruction patterns in HTML, never grant authority.

The rules can miss instructions and can flag benign prose. A negative result
does not establish safety. No fetched content invokes actions or a classifier.
"""

import re
import unicodedata
from html.parser import HTMLParser


_RULES = [
    ("override_instructions_en", "Requests overriding prior or system instructions",
     r"\b(?:ignore|disregard|forget)\s+(?:(?:all|the|your)\s+)?(?:previous|prior|system)\s+(?:instructions|prompts|rules)\b"),
    ("override_instructions_fr", "Requests overriding prior or system instructions in French",
     r"\b(?:ignore[zr]?|oublie[zr]?)\s+(?:(?:toutes?|les|vos|tes)\s+){0,2}(?:instructions|consignes)\s+(?:precedentes|anterieures|systeme)\b"),
    ("agent_action_en", "Addresses an agent with an action instruction",
     r"\b(?:assistant|agent|chatgpt|llm)\s*[:,!]\s*(?:run|execute|call|send|reveal|print|upload|delete)\b"),
    ("agent_action_fr", "Addresses an agent with an action instruction in French",
     r"\b(?:assistant|agent|chatgpt|llm)\s*[:,!]\s*(?:execute[zr]?|lance[zr]?|envoie[zr]?|revele[zr]?|supprime[zr]?)\b"),
    ("secret_request_en", "Requests disclosing credentials or secret values",
     r"\b(?:send|reveal|print|upload|exfiltrate)\s+(?:(?:me|your|the|all|environment|system)\s+){0,3}(?:api[ _-]?keys?|credentials|secrets|tokens|passwords)\b"),
    ("secret_request_fr", "Requests disclosing credentials or secret values in French",
     r"\b(?:envoie[zr]?|revele[zr]?|affiche[zr]?)\s+(?:(?:les|vos|tes|tous|toutes|mes)\s+){0,3}(?:cles\s+api|identifiants|secrets|jetons|mots\s+de\s+passe)\b"),
]
_PATTERNS = [(rule, reason, re.compile(pattern, re.IGNORECASE)) for rule, reason, pattern in _RULES]
_BLOCKS = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "title", "br"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_QUOTED = {"pre", "code", "blockquote", "q"}
_HIDDEN_STYLE = re.compile(
    r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0|font-size\s*:\s*0(?:px|em|rem|%)?)\s*(?:!important\s*)?(?:;|$)",
    re.IGNORECASE,
)
_MAX_SIGNALS = 20
_MAX_SAMPLE = 240


class _InstructionObserver(HTMLParser):
    def __init__(self, source_url):
        super().__init__()
        self.source_url = source_url
        self.frames: list[tuple[str, bool, bool, bool]] = []
        self.chunks: list[str] = []
        self.chunk_source: dict | None = None
        self.signals: list[dict] = []
        self.truncated = False
        self.sample: str | None = None

    def _state(self):
        return self.frames[-1][1:] if self.frames else (False, False, False)

    def _source(self, tag, hidden, **extra):
        line, column = self.getpos()
        return {"url": self.source_url, "line": line, "column": column,
                "tag": tag, "hidden": hidden, **extra}

    def _observe(self, text, source):
        # Accent folding covers the explicit French patterns, not translations.
        folded = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
        for rule, reason, pattern in _PATTERNS:
            match = pattern.search(folded)
            if match:
                if len(self.signals) >= _MAX_SIGNALS:
                    self.truncated = True
                    continue
                self.signals.append({"rule": rule, "basis": "rule", "method": "deterministic_patterns",
                                     "reason": reason, "source": source})
                if self.sample is None:
                    start = max(0, match.start() - 40)
                    self.sample = text[start:start + _MAX_SAMPLE]

    def _flush(self):
        if self.chunks:
            self._observe("".join(self.chunks), self.chunk_source)
        self.chunks = []
        self.chunk_source = None

    def handle_starttag(self, tag, attrs):
        parent_hidden, parent_quoted, parent_skipped = self._state()
        values = dict(attrs)
        hidden = (
            parent_hidden or tag == "template" or "hidden" in values
            or (values.get("aria-hidden") or "").lower() == "true"
            or bool(_HIDDEN_STYLE.search(values.get("style") or ""))
        )
        quoted = parent_quoted or tag in _QUOTED
        skipped = parent_skipped or tag == "style" or (tag == "script" and values.get("type") not in {"application/json", "application/ld+json"})
        state = (hidden, quoted, skipped)
        if tag in _BLOCKS or state != self._state():
            self._flush()
        if not skipped and (hidden or not quoted):
            for attribute, value in attrs:
                if value:
                    self._observe(value, self._source(tag, hidden, attribute=attribute))
        if tag not in _VOID:
            self.frames.append((tag, *state))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.frames) - 1, -1, -1) if self.frames[i][0] == tag), None)
        if index is not None:
            new_state = self.frames[index - 1][1:] if index else (False, False, False)
            if tag in _BLOCKS or new_state != self._state():
                self._flush()
            del self.frames[index:]

    def handle_data(self, data):
        hidden, quoted, skipped = self._state()
        if not skipped and (hidden or not quoted):
            if self.chunk_source is None:
                self.chunk_source = self._source(self.frames[-1][0] if self.frames else "text", hidden)
            self.chunks.append(data)

    def handle_comment(self, data):
        hidden, quoted, skipped = self._state()
        if not skipped and (hidden or not quoted):
            self._observe(data, self._source("comment", True))


def observe_untrusted_content(html: str, *, source_url: str) -> dict:
    """Return additive observations; original audit values are left untouched.

    HTML line/column locations refer to parsed segments or attribute-bearing
    tags. Quoted code/pre/blockquote/q text is excluded unless explicitly hidden.
    Hidden detection uses HTML attributes and inline CSS, not rendered styles.
    """
    parser = _InstructionObserver(source_url)
    parser.feed(html)
    parser.close()
    parser._flush()
    return {"trust": "untrusted", "assessment": "deterministic_rules_only",
            "flagged": bool(parser.signals), "signals": parser.signals,
            "signals_truncated": parser.truncated, "sample": parser.sample}
