"""Conservative challenge evidence from untrusted HTML, without executing it.

Only the known SiteGround path plus a human-verification prompt is supported.
This is a local heuristic, not proof of the provider or a general bot detector.
"""

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


_HUMAN_PROMPT = re.compile(
    r"(?:please )?(?:verify (?:that )?you are (?:a )?human|human verification)[.!?]?",
    re.IGNORECASE,
)


class _ChallengeExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.siteground_resource = False
        self.human_prompt = False
        self._prompt_tag: str | None = None
        self._prompt_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"title", "h1"}:
            self._prompt_tag = tag
            self._prompt_chunks = []
        attribute = {"script": "src", "form": "action"}.get(tag)
        resource = dict(attrs).get(attribute) if attribute else None
        if resource:
            try:
                path = urlsplit(resource).path
            except ValueError:
                return
            if path.startswith("/.well-known/sgcaptcha/"):
                self.siteground_resource = True

    def handle_data(self, data):
        if self._prompt_tag:
            self._prompt_chunks.append(data)

    def handle_endtag(self, tag):
        if tag == self._prompt_tag:
            text = " ".join("".join(self._prompt_chunks).split())
            if _HUMAN_PROMPT.fullmatch(text):
                self.human_prompt = True
            self._prompt_tag = None


def detect_challenge_page(html: str) -> dict | None:
    """Return provider/reason evidence only when both known signals are present.

    A status code, a generic CAPTCHA widget or a prose mention alone is not
    evidence that the requested page was replaced by a challenge interstitial.
    Resource attributes are inspected as data; no script or form is invoked.
    """
    parser = _ChallengeExtractor()
    parser.feed(html)
    parser.close()
    if parser.siteground_resource and parser.human_prompt:
        return {
            "provider": "siteground",
            "reasons": ["siteground_challenge_resource", "human_verification_prompt"],
        }
    return None
