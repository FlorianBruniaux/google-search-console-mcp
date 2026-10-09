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
