"""Synthetic highlighted commands must survive visible-text extraction intact."""
import pytest

from gsc_mcp.content_extraction import extract_html


@pytest.mark.parametrize('markup,expected', [
    ('<pre><code><span>tool install </span><span>-g </span><span>@example</span>'
     '<span>/test-cli</span></code></pre>', 'tool install -g @example/test-cli'),
    ('<pre><code><span>irm https</span><span>:</span><span>//example.test/install.ps1 </span>'
     '<span>|</span><span> iex</span></code></pre>', 'irm https://example.test/install.ps1 | iex'),
    ('<p>Check <code><span>tool --</span><span>version</span></code> first.</p>',
     'Check tool --version first.'),
    ('<pre>  tool<span>\t</span><span>--flag</span>\n  next &amp;&amp; last\n</pre>',
     '  tool\t--flag\n  next && last\n'),
])
def test_highlighted_code_preserves_tokens_and_source_whitespace(markup, expected):
    # Inserting separators at inline-node boundaries corrupts literal commands.
    result = extract_html(markup, 'https://example.test/guide')
    assert result['status'] == 'extracted'
    assert result['text'] == expected


@pytest.mark.parametrize('markup', [
    '<pre><code><div><span>tool </span><span>--version</span></div>'
    '<div><span>next </span><span>--help</span></div></code></pre>',
    '<pre>tool --version<br>next --help</pre>',
])
def test_code_line_elements_do_not_concatenate_separate_commands(markup):
    result = extract_html(markup, 'https://example.test/guide')
    assert result['text'].splitlines() == ['tool --version', 'next --help']


def test_skipped_content_cannot_change_code_state_or_leak_into_text():
    markup = ('<nav><pre><code>hidden</code></pre></nav><p>Before</p>'
              '<pre><code><span>tool</span><script>ignored</script><style>hidden</style>'
              '<span> --version</span></code></pre><p>After</p>')
    result = extract_html(markup, 'https://example.test/guide')
    assert result['text'] == 'Before tool --version After'


def test_incremental_unclosed_code_keeps_collected_text():
    from gsc_mcp.tools.content import _TextExtractor

    parser = _TextExtractor()
    parser.feed('<p>Before</p><pre><code><span>tool --')
    parser.feed('</span><span>version</span>')
    assert parser.text == 'Before tool --version'
    parser.feed('</code></pre><p>After</p>')
    assert parser.text == 'Before tool --version After'


def test_empty_code_is_not_reported_as_extracted_content():
    result = extract_html('<pre><code> \n\t </code></pre>', 'https://example.test/guide')
    assert result['status'] == 'no_visible_text'
    assert result['text'] == ''


@pytest.mark.parametrize('breaks', ['<br><br>', '<br/><br/>'])
def test_repeated_explicit_breaks_preserve_blank_code_lines(breaks):
    result = extract_html('<pre>a' + breaks + 'b</pre>', 'https://example.test/guide')
    assert result['text'] == 'a\n\nb'
