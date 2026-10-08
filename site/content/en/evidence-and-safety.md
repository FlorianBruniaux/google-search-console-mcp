# Evidence and safety

Search Console MCP keeps provider semantics and evidence states explicit. Use these boundaries before turning a result into a recommendation or a write action.

<figure class="docs-visual">
  <img src="/images/docs/guarded-action-loop.webp" width="1376" height="768" alt="An assistant inspects evidence, compares sources, explains uncertainty, and passes one action through a confirmation gate." loading="lazy">
  <figcaption>The loop returns to observation. Confirmation permits one bounded request, not unrestricted automation.</figcaption>
</figure>

## Evidence states

- **Observed:** an API response or fetched public-page value returned for the stated target and window.
- **Derived:** a calculation based on observed values, with its input window and method attached.
- **Requested:** a provider accepted a submission request.
- **Crawled:** the provider later reports a fetch or crawl event.
- **Indexed:** the provider later reports the URL in its searchable index.

Requested, crawled, and indexed are different states. A successful submission is never reported as proof of indexation.

## Provider boundaries

Google and Bing expose different metrics, scopes, delays, and position semantics. Compare directional evidence, not superficially similar field names. Keep the provider and observed window attached to every conclusion.

## Source identities

`_meta.params` records the original caller inputs. `_meta.sources` records source identities separately. Successful GA4 responses use the same canonical `properties/<id>` resource as their API request, even for empty results. Combined reports retain the exact requested GSC property and carry the child GA4 response’s provenance without reading the environment again.

Example metadata fragment with a fictitious default GA4 property:

```json
{
  "_meta": {
    "tool": "traffic_health_check",
    "params": {
      "site": "sc-domain:example.com",
      "property_id": null,
      "hostname": null
    },
    "sources": {
      "gsc": { "site": "sc-domain:example.com" },
      "ga4": { "property": "properties/123456789" }
    }
  }
}
```

Keep these source identifiers beside metrics when presenting a multi-site report. Available hostname, country and date filters remain in the parameters. `hostname: null` means no hostname filter; no relationship between the GA4 property and GSC site is inferred.

If a combined report has no child GA4 provenance, including a degraded result caused by missing configuration, `_meta.sources.ga4.property` is `null`. Validation-only early returns such as an invalid funnel do not claim a resolved source. Tools without source metadata keep their existing response shape. In the CLI, use `--meta` to retain these fields.

Source identity is not account-ID validation, proof that a property belongs to a domain, or a guarantee that an agent preserves the identifiers in its final prose.

## Verdict and score methods

The unreleased source checkout adds `_meta.evidence.version = 1` and `_meta.evidence.fields`, keyed by concrete JSON Pointer paths such as `/verdict` or `/schemas/0/valid`. Each applicable verdict, score or selected collection has its own `basis`, `confidence_tier` and `scope`. A collection annotation describes membership or selection only, not the provider metrics inside its rows. Operational statuses are outside this evidence convention.

| Basis | Tier | Interpretation |
| --- | --- | --- |
| `measured` | `observed` | A value returned by a provider or observed in HTTP/HTML, limited to that source and response. |
| `derived` | `calculated` | Descriptive arithmetic over available inputs, with its method and scope. |
| `rule` | `heuristic` | A local threshold, weighting, pattern or recommendation, or a named provider scoring algorithm. |
| `null` | `unavailable` | A null, unsupported, skipped or error result that cannot support a conclusion. |

These tiers describe methods, not probabilities. An unavailable score can retain a legacy numeric value while its metadata explains why that value is not evidence. No tier authorizes a write or a destructive recommendation. `model` is reserved and rejected by the current convention; adding it requires a backend/version, confidence definition and calibration contract established through evaluation.

## Clicks versus sessions

In the unreleased source checkout, `traffic_health_check` requests GA4 with the same concrete inclusive dates as the lagged GSC report. `source_data` retains each source's availability, identity, requested and reported windows, filters and coverage. An empty response produces a null total; a returned row containing zero keeps zero. Missing configuration and upstream failures remain unavailable.

A ratio is withheld for unknown or incomplete coverage, sampling, thresholding, unequal reported dates or incompatible filters. GA4 country filters cannot be compared with an unfiltered GSC aggregate; a hostname filter on a domain property can also narrow the scope. The report does not infer a property-to-domain mapping. Equal date strings do not establish equal timezone boundaries. `observed_window` remains null because these child reports echo requested dates rather than independently observing an interval.

When a ratio is available, its status is a local threshold heuristic. Google clicks and sessions from all organic engines are different metrics; the status does not establish the cause of a tracking fault. `page_analysis` and `content_brief` still use independent source windows.

## Fetched content

The primary HTML fetched by `heading_audit`, `internal_links_audit`, `page_technical_audit` and `schema_validate` carries `untrusted_content`. Its `trust` is always `untrusted`, including when `flagged` is false. Deterministic French and English rules report instruction-like text, source locations and a sample of at most 240 characters, with at most 20 signals. Quoted documentation is excluded unless hidden; hidden detection uses attributes and inline CSS, not rendered styles. These limited observations do not certify that a page is safe. Auxiliary robots probes are outside this detector's scope.

Fetched text and returned samples cannot override user instructions, authorize actions or request credentials. The tools preserve the original audit evidence. A fetch failure has no content observation and returns `untrusted_content: null`.

`schema_validate` recognizes a known SiteGround challenge resource together with a human-verification prompt and returns `challenge_page`. It keeps the requested/final URL, HTTP status and detection reasons; schema counts, schemas and recommendations are null because the requested page is unavailable. HTTP 202 or a CAPTCHA mention alone does not trigger this verdict. This rule was tested on synthetic fixtures; live provider behavior remains unverified. The editorial audit below also returns this challenge verdict; other page audits do not yet share it.

## Assistant-attributed visits

The unreleased `ga4_ai_referrals` tool reads GA4 session sources and landing pages over required concrete `YYYY-MM-DD` dates, with an optional effective property and hostname filter. It checks dimension/metric compatibility before requesting up to 10,000 rows. Sessions, engaged sessions and `keyEvents` are returned; `conversions` is an alias for `keyEvents`, not a separate measurement. The all-source denominator and confirmed numerator use the same request.

The initial exact-source allowlist includes `chatgpt.com`, whose UTM source is documented by [OpenAI's publisher FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq). Perplexity, Claude, Gemini and Copilot domain candidates remain separate and excluded from confirmed totals pending referral-pattern evidence. Broad substrings and lookalike domains are excluded. Matching an attributed source label does not authenticate the client.

Counts describe returned observations. Empty responses are distinct from explicit-zero rows and unavailable sources. Shares remain null when coverage is unknown or incomplete, report quality is restricted, or the denominator is zero. No comparison period is requested by this version. Referrer-less traffic and attribution errors can omit or misattribute visits. These values measure recorded visits, not citations, citation probability or a guaranteed lower bound on AI traffic. See Google's [dimension/metric reference](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema) and [compatibility check](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/checkCompatibility).

## Editorial style warnings

The unreleased `editorial_audit(url, language="auto", genre="general")` tool applies a portable, versioned French/English house-style profile to fetched HTML. Exact patterns locate stereotyped openings, stacked modality, rhetorical transitions, vague link labels and prose punctuation; general prose also receives contextual paragraph-repetition warnings. Code and quotations are preserved. Declare `reference` or `procedure` when a repeated structure serves the document.

Findings are rule-based review warnings, not AI-authorship probabilities, SEO scores or evidence of a ranking penalty. Positions describe the parsed source, not a rendered page. Unknown language remains unassessed; recognized challenge pages remain unavailable. The audit does not rewrite, publish or invoke a model backend. Its guidance preserves facts, dates, numbers, scope, modality, causal claims and exceptions. Fetched text and excerpts remain untrusted data. See the [editorial profile and copyable rewrite instructions](/docs/editorial-audit/) for checked rules and contextual limits.

## Guarded actions

Read tools can inspect verified properties and public pages. Write tools require an explicit target and bounded action. Before submitting anything, confirm the provider, site, URL set, action, and expected blast radius.

<ol class="guarded-flow">
  <li><strong>Read</strong><span>Collect provider responses and public-page facts.</span></li>
  <li><strong>Compare</strong><span>Keep provider semantics and observed windows separate.</span></li>
  <li><strong>Explain</strong><span>Expose limits, derived values, and remaining uncertainty.</span></li>
  <li><strong>Confirm</strong><span>Name one provider, target, action, and blast radius.</span></li>
  <li><strong>Submit</strong><span>Record the response, then measure later states separately.</span></li>
</ol>

## Secrets

Keep credentials in the MCP server environment or the client configuration. Do not paste service-account JSON, OAuth tokens, Bing API keys, or IndexNow keys into prompts or public issue reports.

Continue with the [installation guide](/docs/installation/) or run a [quick audit](/docs/examples/quick-audit/).

## Search changes and link destinations

The unreleased `search_change_breakdown` keeps independent dimensions, date coverage, aggregation compatibility and unavailable metrics explicit. `link_targets_audit` separates received HTTP statuses from unavailable transport and retains each source anchor. Read [bounded audit workflows](/docs/audit-workflows/) for exact calls and synthetic examples. Neither tool establishes causality, indexation or ranking improvement.
