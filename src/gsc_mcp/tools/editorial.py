"""Read-only editorial house-style audit with untrusted URL and caller draft observations."""
import json

import httpx

from gsc_mcp.content_trust import observe_untrusted_content
from gsc_mcp.editorial import PROFILE_ID, PROFILE_VERSION, REWRITE_GUIDANCE, analyze_html
from gsc_mcp.meta import with_meta
from gsc_mcp.tools.editorial_drafts import MAX_DRAFT_CHARACTERS, MAX_DRAFT_BLOCKS, analyze_draft
from gsc_mcp.page_challenges import detect_challenge_page
from gsc_mcp.url_safety import URLSafetyError, fetch_html_following_redirects


def editorial_audit(url: str | None = None, language: str = 'auto', genre: str = 'general', *, text: str | None = None, format: str = 'plain') -> str:
    """Review narrow FR/EN editorial house rules, preserving quoted examples/code.

    Supply exactly one source: url, or text with format plain/markdown.
    Drafts use a bounded Markdown subset with original Unicode source spans.
    language: auto (declared HTML lang only; unavailable for drafts), fr, en. genre: general, reference,
    procedure. Findings are deterministic heuristic warnings, not authorship or
    search-ranking scores. No rewriting, publishing or model calls occur.
    """
    params = {'url': url, 'language': language, 'genre': genre}
    result = {'url': url, 'final_url': None, 'http_status': None,
              'method': {'profile_id': PROFILE_ID, 'profile_version': PROFILE_VERSION,
                         'type': 'deterministic_rules', 'language': None, 'genre': genre},
              'assessment': 'not_assessed', 'findings': None, 'findings_truncated': False,
              'metrics': None, 'untrusted_content': None, 'rewrite_guidance': list(REWRITE_GUIDANCE)}

    if text is not None:
        params.update(format=format, text_characters=len(text) if isinstance(text, str) else None)
        result.update(source={'origin': 'caller', 'format': format},
                      input_limits={'max_characters': MAX_DRAFT_CHARACTERS, 'max_blocks': MAX_DRAFT_BLOCKS},
                      input_truncated=False)

    def output():
        return json.dumps(with_meta(result, tool='editorial_audit', params=params))

    if language not in {'auto','fr','en'} or genre not in {'general','reference','procedure'}:
        result.update(verdict='invalid_input', error='language must be auto/fr/en; genre must be general/reference/procedure')
        return output()
    invalid_source = ((url is None) == (text is None)
                      or (url is not None and (not isinstance(url, str) or not url.strip()))
                      or (text is not None and not isinstance(text, str)))
    if invalid_source or format not in {'plain', 'markdown'} or (url is not None and format != 'plain'):
        result.update(verdict='invalid_input', error='Supply exactly one nonempty url or text source; draft format must be plain/markdown.')
        return output()
    if text is not None:
        if len(text) > MAX_DRAFT_CHARACTERS:
            result.update(verdict='invalid_input', error='draft exceeds maximum input characters')
            return output()
        try:
            result.update(analyze_draft(text, format=format, language=language, genre=genre))
        except ValueError as exc:
            result.update(verdict='invalid_input', error=str(exc))
        return output()
    try:
        html, status, final_url = fetch_html_following_redirects(url)
    except (URLSafetyError, httpx.HTTPError) as exc:
        if isinstance(exc, httpx.HTTPStatusError):
            result.update(http_status=exc.response.status_code, final_url=str(exc.request.url))
        result.update(verdict='fetch_error', error=str(exc))
        return output()
    result.update(final_url=final_url, http_status=status,
                  untrusted_content=observe_untrusted_content(html, source_url=final_url))
    challenge = detect_challenge_page(html)
    if challenge:
        result.update(verdict='challenge_page', challenge=challenge)
        return output()
    result.update(analyze_html(html, source_url=final_url, language=language, genre=genre))
    if result['verdict'] != 'checked':
        result['assessment'] = 'not_assessed'
    return output()
