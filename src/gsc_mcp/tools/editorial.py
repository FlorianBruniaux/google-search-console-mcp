"""Read-only editorial house-style audit with untrusted HTML observations."""
import json

import httpx

from gsc_mcp.content_trust import observe_untrusted_content
from gsc_mcp.editorial import PROFILE_ID, PROFILE_VERSION, REWRITE_GUIDANCE, analyze_html
from gsc_mcp.meta import with_meta
from gsc_mcp.page_challenges import detect_challenge_page
from gsc_mcp.url_safety import URLSafetyError, fetch_html_following_redirects


def editorial_audit(url: str, language: str = 'auto', genre: str = 'general') -> str:
    """Review narrow FR/EN editorial house rules, preserving quoted examples/code.

    language: auto (declared HTML lang only), fr, en. genre: general, reference,
    procedure. Findings are deterministic heuristic warnings, not authorship or
    search-ranking scores. No rewriting, publishing or model calls occur.
    """
    params = {'url': url, 'language': language, 'genre': genre}
    result = {'url': url, 'final_url': None, 'http_status': None,
              'method': {'profile_id': PROFILE_ID, 'profile_version': PROFILE_VERSION,
                         'type': 'deterministic_rules', 'language': None, 'genre': genre},
              'assessment': 'not_assessed', 'findings': None, 'findings_truncated': False,
              'metrics': None, 'untrusted_content': None, 'rewrite_guidance': list(REWRITE_GUIDANCE)}

    def output():
        return json.dumps(with_meta(result, tool='editorial_audit', params=params))

    if language not in {'auto','fr','en'} or genre not in {'general','reference','procedure'}:
        result.update(verdict='invalid_input', error='language must be auto/fr/en; genre must be general/reference/procedure')
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
