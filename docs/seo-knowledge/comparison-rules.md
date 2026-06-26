# SEO Drift Comparison Rules

Source: adapted from `scripts/drift_compare.py` in claude-seo (Dan Colta, MIT).
These 17 rules are implemented in `src/gsc_mcp/tools/drift.py`.

## CRITICAL rules (rules 1-8)

Changes with immediate ranking impact.

| # | Rule ID | Trigger condition |
|---|---------|-------------------|
| 1 | `schema_removed` | Schema/JSON-LD was present in baseline, zero blocks now |
| 2 | `canonical_changed` | Canonical URL changed from one non-null value to a different one |
| 3 | `canonical_removed` | Canonical was present, now absent or empty |
| 4 | `noindex_added` | Robots meta tag gained "noindex" since baseline |
| 5 | `h1_removed` | H1 was present, now absent |
| 6 | `h1_changed` | H1 similarity ratio (SequenceMatcher) < 0.5 |
| 7 | `title_removed` | Title tag was present, now absent |
| 8 | `status_code_error` | HTTP status changed from 2xx/3xx to 4xx/5xx |

## WARNING rules (rules 9-14)

Require monitoring; may affect CTR or performance signals.

| # | Rule ID | Trigger condition |
|---|---------|-------------------|
| 9 | `title_changed` | Title text changed (both sides non-empty, different) |
| 10 | `meta_description_changed` | Meta description changed (both sides non-empty, different) |
| 11 | `cwv_regressed` | LCP, INP, or CLS p75 field value worsened by more than 20% |
| 12 | `perf_score_dropped` | Lighthouse performance score dropped 10+ points (skipped: CrUX field data does not include Lighthouse scores) |
| 13 | `og_tags_removed` | All Open Graph tags removed |
| 14 | `schema_modified` | Schema present in both but SHA-256 hash differs |

## INFO rules (rules 15-17)

Informational; usually positive or low-urgency signals.

| # | Rule ID | Trigger condition |
|---|---------|-------------------|
| 15 | `schema_added` | No schema in baseline, now schema present |
| 16 | `h2_structure_changed` | H2 list changed (count or content) |
| 17 | `content_hash_changed` | SHA-256 of full HTML body changed |

## Implementation notes

- Rules apply to the diff between the stored baseline and the current live fetch.
- Each finding has: `rule`, `severity`, `triggered` (bool), `old_value`, `new_value`, `message`.
- Only `triggered: true` findings appear in `triggered_findings`; all 17 appear in `all_findings`.
- CWV rules (11) require `CRUX_API_KEY` to be set; they auto-skip otherwise.
- Rule 12 is structurally retained but always returns not-triggered (CrUX provides field data, not Lighthouse lab scores).
