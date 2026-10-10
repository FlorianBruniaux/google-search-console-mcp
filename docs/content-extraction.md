# Optional main-content extraction

`content_quality(url)` retains the existing visible-text extractor and scores. To evaluate a second profile, install the optional extra and select it explicitly:

```sh
uvx --from 'gsc-mcp-tools[content]' gsc-cli content-quality --url https://example.com/article --extractor trafilatura-precision
```

For an MCP client, add `--with trafilatura==2.3.1` to its `uvx gsc-mcp-tools` invocation, then pass `extractor="trafilatura-precision"` to `content_quality`. The default installation does not include this dependency. Supported Trafilatura versions are 2.3.x, starting at 2.3.1.

The adapter processes HTML returned by the existing URL safety and size controls. It makes no second fetch. Its explicit settings exclude comments, include tables, prefer precision, disable fallback extraction and disable deduplication. A per-call copy of the library configuration limits extracted tree size to 20,000 elements; decoded HTML and extracted text each fit 2 MiB UTF-8. No global configuration or cross-site cache is modified. [Trafilatura's API reference](https://trafilatura.readthedocs.io/en/latest/corefunctions.html) describes these extraction choices.

Responses include the selected profile, library version, options, requested source URL, hash of decoded HTML and fetch completion time. The requested URL is not asserted to be the final redirect URL, and the hash is not a hash of original compressed network bytes. Extracted text is used internally for the existing heuristics, not returned in a new unrestricted text field. Source text remains untrusted data.

Missing dependencies, unsupported versions, extraction exceptions, no returned main content, output limits and non-success HTTP status make the optional assessment unavailable. No quality score or zero word count is substituted. `empty_input` means the acquired HTML string is empty; `no_visible_text` means the existing parser returned no text; `no_main_content_returned` means the optional algorithm selected no text. The latter does not distinguish boilerplate-only content from omitted valid content. Main-content recall and partial extraction remain unknown until independently annotated.

Local repeated and interleaved calls exercise the actual optional package on controlled article HTML. They do not establish superiority on FR/EN article, product, local-service, forum or JavaScript-shell sites. #6 and #41 retain the authorized human-annotation, inclusion/omission, memory and adoption gates. Do not change the default profile from these fixtures. Extraction and similarity cannot establish authorship, indexing or harmful cannibalization.

## Offline annotated comparison

From a checkout installed with the optional content extra, run the supplied synthetic smoke fixture:

```sh
python scripts/eval_content_extraction.py --dataset tests/fixtures/content_extraction_eval/manifest.synthetic.json --split held_out
```

The runner invokes both existing profiles on each selected local HTML file, without fetching URLs or calling a model. The smoke file and annotation identities are synthetic test markers. They demonstrate the runner; `release_quality` remains `UNKNOWN` and `synthetic_release_eligible` is false. The default extractor remains visible text.

For a real comparison, supply the same version-1 manifest structure with authorized UTF-8 HTML under its directory. `provenance` is `human` or `synthetic`. Each case declares its source URL, relative `html_path`, raw-byte `html_sha256`, language (`fr` or `en`), page type (`article`, `product`, `local_service`, `forum`, `js_shell`), source authorization and distinct annotator/reviewer identities. `independent_of_extractors` must declare that labels were prepared without consulting extractor outputs. Authorization, identity, independence and freezing are recorded declarations, not authenticated approvals.

Assign `train`, `tuning` and `held_out` before tuning. Group related task scenarios, sites and page variants with `task_family`, `site_family` and `page_family`; each family must belong to one split. Page type and language describe coverage, rather than family identity. The runner rejects a family crossing splits or identical HTML appearing more than once. Freeze the manifest, its HTML hashes and the `protocol` inclusion, omission and resource criteria before comparison; `frozen_before_tuning: true` records that declaration but does not prove its chronology. No numeric release thresholds are supplied by this script.

`include` contains main-content snippets expected in the extracted text. `omit` contains snippets with `text` and `kind` (`template`, `comment`, `other`) expected to be excluded. Snippets are case-folded and whitespace-collapsed for substring matching. They must occur in the supplied HTML parser text data; this occurrence check includes script/style data and does not judge main-content relevance. Duplicate, conflicting or nested snippets are rejected to avoid counting the same labeled fragment twice. An empty label list is permitted, for example a JS shell with no annotated main content, and produces a null metric for that dimension.

`inclusion_recall` is the fraction of labeled inclusion snippets returned; `omission_leakage` is the fraction of labeled omission snippets returned. Per-snippet booleans and omission counts by kind allow review of those fractions. These measures do not estimate whole-content recall or extraction precision. `annotation_coverage: partial` means some supplied inclusion snippets were missed, while `complete_labeled_snippets` means all supplied inclusion snippets matched. Missing packages, failed extraction and no returned text retain their status with null metrics, rather than fabricated zero scores. Downstream content-quality warnings are `not_measured`; they require a separate comparison against annotated warning targets.

Reports record manifest hash/path, HTML hash/path/byte count, profile version/options, interpreter/platform and coverage for the selected split. Raw HTML hashes differ from the adapter's decoded-HTML hash when serialization bytes differ. HTML is decoded strictly as UTF-8; the runner performs no acquisition or JS rendering. Extracted text and annotation snippets are not copied into the report. Treat all source content as untrusted data.

The resource fields are a single `wall_seconds` observation and `python_allocation_peak_bytes` from `tracemalloc` during each extraction call. Fixed profile order, first-use imports and caches affect these values. Traced allocations exclude untracked native allocations and total process RSS; reading and validating the corpus happens before measurement. This provides observations to review against frozen resource criteria, without claiming a comparative performance verdict.

Input limits are 100 cases, 100 snippets per case, 10,000 characters per string, 2 MiB per manifest or HTML file and 16 MiB total HTML. Output is capped at 2 MiB. Absolute HTML paths, parent traversal, symlinks escaping the manifest directory, non-UTF-8 files, duplicate JSON keys, nonfinite JSON values, hash mismatches and an empty selected split fail before comparison. The caller saves reports where local corpus provenance may be disclosed. Real independently annotated FR/EN page families, acceptable quality/resource targets, downstream warnings and the adoption decision remain required under #6 and #41.
