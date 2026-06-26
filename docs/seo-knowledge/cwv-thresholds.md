# Core Web Vitals Thresholds

Reference for the thresholds used in gsc-mcp CrUX tools and drift monitoring.
Source: adapted from `CWV_THRESHOLDS` dict in `scripts/pagespeed_check.py` in claude-seo (MIT),
cross-referenced against Google documentation. Updated for INP replacing FID (March 2024).

## Field thresholds (Chrome UX Report / real-user data)

| Metric | Good | Needs Improvement | Poor | Unit | Notes |
|--------|------|-------------------|------|------|-------|
| LCP (Largest Contentful Paint) | <= 2500 | 2500-4000 | > 4000 | ms | Main content load |
| INP (Interaction to Next Paint) | <= 200 | 200-500 | > 500 | ms | Replaces FID since March 2024 |
| CLS (Cumulative Layout Shift) | <= 0.1 | 0.1-0.25 | > 0.25 | unitless | Visual stability |
| FCP (First Contentful Paint) | <= 1800 | 1800-3000 | > 3000 | ms | Perceived load start |
| TTFB (Time to First Byte) | <= 800 | 800-1800 | > 1800 | ms | Server response |

## Key notes

- FID (First Input Delay) was deprecated in March 2024 and replaced by INP. Google
  fully removed FID from CrUX data in March 2024. Any baseline capturing FID values
  should be treated as legacy data.
- CrUX reports p75 values (75th percentile). A page passes a Core Web Vitals
  assessment when its p75 for all three Core Web Vitals (LCP, INP, CLS) are in the
  Good range.
- Lab metrics (Lighthouse) differ from field metrics. gsc-mcp uses field data
  (CrUX API) for both `crux_page_vitals` and drift monitoring.

## Drift monitoring usage

The `drift_compare` tool (rule 11, `cwv_regressed`) flags a WARNING when any CrUX
p75 metric worsens by more than 20% since the baseline snapshot. The comparison
uses LCP, INP, and CLS as the three Core Web Vitals.
