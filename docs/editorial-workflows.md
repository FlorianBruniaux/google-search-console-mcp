# Review drafts and proposed rewrites

Draft inputs for `editorial_audit` and the new `rewrite_fidelity_check` are unreleased source features. The source checkout exposes 87 tools; published release 1.3.1 has 85 and supports URL editorial audits. Follow [installation](installation.md) for a source checkout. These examples are caller-supplied explanatory passages, with no live request or publication.

## Audit a draft before publication

```python
editorial_audit(text="The catch? Read [click here](https://example.com/guide/).",
                language="en", genre="general", format="markdown")
editorial_audit(text="Le hic ? Le texte est à relire.", language="fr", format="plain")
```

The additive signature is `editorial_audit(url=None, language="auto", genre="general", *, text=None, format="plain")`. Supply exactly one of `url` or `text`; selection uses null, so an empty string counts as a supplied source. Existing positional URL calls retain their contract. URL mode permits `format="plain"` only, and still fetches HTML. Draft mode accepts `plain` or `markdown` and never fetches link destinations, reads files, executes HTML or renders content. Caller text remains untrusted data.

Declare `language="fr"` or `"en"`. Draft `auto` returns `language_unavailable`, including when Markdown frontmatter contains a language field. Findings and metrics stay null when unassessed. Explicit-language empty eligible content returns `empty_content`. `genre="reference"` or `"procedure"` retains the profile's structural exceptions. The same versioned [editorial profile](editorial-audit.md) supplies the rule warnings.

Each input is limited to 100,000 Unicode codepoints and 2,000 parsed blocks, including exclusion boundaries. Over-limit drafts return `invalid_input` rather than a partial audit. Outputs retain the 50-finding cap, 240-character excerpts and `findings_truncated`. Draft `url`, `final_url` and `http_status` are null; `source.origin=caller` and `source.format` disclose the input. Metadata retains format and character count without copying raw draft text.

Markdown uses a bounded subset, not a complete CommonMark parser. It supports paragraphs, ATX headings, standalone list items, basic paired emphasis, punctuation escapes, bounded inline links and defined reference links. Code, quotations, images, raw HTML and actual link destinations are excluded. Exclusion boundaries interrupt repetition checks. Tables, setext headings, autolinks, nested labels and other unsupported syntax are disclosed in `method.coverage` and can remain literal prose. Parser ceilings include nesting 8, link labels 1,000 characters, destinations 2,048 characters and inline HTML closing scans 4,096 codepoints. Review coverage before interpreting warnings.

Draft findings use `location.basis=original_source_span`: `source_start` and `source_end` are zero-based half-open Unicode-codepoint offsets into the original input; line is 1-based and column 0-based. A span can contain intervening markup. `normalized_text_start`/`normalized_text_end` index normalized text, not rendered coordinates. Trust signals locate the original segment start rather than the exact instruction phrase. A clean rule result covers only eligible passages and implemented patterns.

## Compare an original and a proposed revision

```python
rewrite_fidelity_check(
    original="The estimate may reach 12 days if the source remains available.",
    revised="The estimate reaches 15 days.",
    language="en", format="plain",
)
```

The signature is `rewrite_fidelity_check(original: str, revised: str, language: str = "en", format: str = "plain") -> str`. Each passage must be nonempty and at most 20,000 characters. Language is explicit `en` or `fr`; format is `plain` or `markdown`. Invalid inputs return `verdict=invalid_input`, `assessment=not_assessed` and null findings.

A valid call returns `verdict=compared` and a mechanical assessment. Finding categories are `number_unit`, `date`, `url`, `code`, `quotation`, `negation`, `modality`, `condition` and `absolute`; operations are `changed`, `context_changed`, `removed` and `added`. Findings retain original/revised literal spans, aligned bounded passages, the matching method and `context_review_required=true`. Missing sides are null. Source offsets remain full spans even when the returned literal is a truncated prefix. Extraction checks at most 500 occurrences per side; output returns at most 100 findings and 100 parsing notes, with 240-character literals, excerpts and aligned passages. Inspect `budgets`, counts, parsing notes, `analysis_truncated` and `findings_truncated` for scope; capped extraction yields `partial_mechanical_comparison`.

Local lexical anchors compare occurrences and context. Reordering does not automatically imply a changed fact, while equal numerals cannot prove equal referents. EN comma thousands/dot decimals and FR space thousands/comma decimals have declared normalization. Units and currencies are not converted. Numeric dates remain literals: ambiguous order and calendar validity are unassessed. URL extraction is simple and excludes parentheses; this check does not parse complete Markdown. Quotation/code boundaries and finite qualifier lists can miss a change or flag harmless wording.

Read every candidate in its surrounding passage. `semantic_assessment` always leaves fidelity, factual truth, scope and causality `unassessed`, including zero findings. The tool supplies no authorship score, automatic correction, model call, file write or publication. Fixed fixtures establish covered mechanical behavior; real-world accuracy requires a separately labeled original/revision corpus. For observed search windows after a declared edit, use [bounded audit workflows](audit-workflows.md).
