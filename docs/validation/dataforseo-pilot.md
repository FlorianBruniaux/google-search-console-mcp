# C2 DataForSEO pilot: qualified source, live acquisition pending

Issue #86; sequence #112. Prepared 2026-10-11 on baseline `712e1baaabb7a9d0450421bf17410d3b99bfdb81`, after C1 merged in #113.

**Current result:** the official MCP source and a bounded comparison protocol are qualified below. No DataForSEO acquisition, account entitlement, billed cost or quality improvement has been measured. No runtime tool or native connector is added by this record.

## Frozen reference and available access

Official source revision: `1fc6d197f1141cca8d1a242e15804c5adc41916a`; its `package.json` declares `dataforseo-mcp-server` version `3.1.3`. These are source observations, not an installed npm-package or hosted-server version claim.

The official README describes stdio environment credentials and a hosted OAuth endpoint. It exposes documentation tools and generic `api_request`; credentials for stdio use `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD`. The inspected code also accepts the legacy login alias. This pilot uses the current documented names. [Official README](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/README.md), [package declaration](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/package.json).

No DataForSEO tool is callable in this session. Plugin discovery returned no DataForSEO match; that result is not an exhaustive directory claim. Neither login nor password was present in this shell's environment. Other private configuration locations were not searched, and no global MCP configuration or installation was changed. Connection/account access remains unverified.

## Capability matrix from inspected source

| Concern | Confirmed source behavior | Pilot consequence |
|---|---|---|
| Response shape | `noAiMode` defaults false and applies an `.ai` suffix. | Set `noAiMode: true` and a standard path; verify the returned shape rather than treating AI-reduced output as a replay source. |
| Task errors | MCP `isError` is set from HTTP status >=400; a task status under HTTP 200 is not checked here. | Review both envelope and task statuses before any diagnostic or next acquisition. |
| Multiple Live tasks | Middleware sends only the first task and adds a warning when the body contains several. | Exactly one task per call; 20 queries × 2 devices requires 40 distinct calls, not one array of 40. |
| Field filtering | Configured fields can trim result objects even when AI mode is disabled; an empty endpoint field list disables this filtering. | Capture effective configuration; retain unfiltered results for this endpoint and preserve separate warning blocks. |
| Response bytes | The client reads text, then the tool parses/reserializes JSON. HTTP status/headers are not separately returned by the tool. | Save the exact delivered MCP content and extracted JSON block; label this a delivered-body replay, not original HTTP-wire bytes. |
| Charging control | The inspected generic schema has no reservation, monetary ceiling, request-key deduplication or attempt budget. | Supervised sequential pilot only; no autonomous paid-agent loop or claim of a server-enforced financial ceiling. |
| Transport | The inspected client uses one `fetch` and reads the whole response, with no explicit timeout, byte cap, redirect policy or retry loop in that path. | Do not assume bounded I/O or client/host retry behavior; timeout/lost/truncated delivery stops further acquisition until reconciliation. |

Sources: [request tool](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/tools/api-request-tool.ts), [HTTP client](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/api/client.ts), [path selection](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/api/path.ts), [Live middleware](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/middleware/api-request/live-endpoint-api-request-middleware.ts), [field configuration](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/config/field-configuration.ts), [result serialization](https://github.com/dataforseo/mcp-server-typescript/blob/1fc6d197f1141cca8d1a242e15804c5adc41916a/src/core/tools/types.ts).

These are static findings. They do not authenticate the hosted service, installed dependencies, real HTTP behavior or a supplier billing ceiling.

## Proposed acquisition scope and cost

Use one approved site's frozen list of 20 real FR queries; Google organic Live Advanced, country-level France, language `fr`, requested depth 10, one desktop and one mobile capture per query. Freeze device/OS pairing and all allowed options before sending. A requested depth of 10 does not promise 10 organic items or complete coverage.

The supplier's public location CSV maps France to `location_code: 2250`, `country_iso_code: FR`, type `Country`. CSV dated 2026-09-01, downloaded through the official locations documentation; SHA-256 `83bcdef1b814c07f542cd4ac08c825e556690335d51ae96c359ff703e661c89b`. [Location contract](https://docs.dataforseo.com/v3/serp/google/locations/), [public CSV](https://cdn.dataforseo.com/v3/locations/locations_serp_google_2026_09_01.csv).

Public Live top10 price checked on 2026-10-11: **0.002 USD per acquisition**, so **40 × 0.002 = 0.08 USD theoretical consumption**. Proposed qualification ceiling: **5 USD**, not yet authorized. Keep the maximum of 40 physical POST attempts independently of that ceiling; no automatic retries, extra queries, premium options, search operators or account purchase/recharge. Recheck applicable pricing before live; a local quotation does not guarantee supplier billing. [Live pricing](https://dataforseo.com/pricing/google-serp/google-organic-serp-api).

Synthetic shape example only, **not a real query or permission to execute**:

```json
{
  "method": "POST",
  "path": "/v3/serp/google/organic/live/advanced",
  "noAiMode": true,
  "data": [
    {
      "keyword": "SYNTHETIC DEMONSTRATION ONLY",
      "location_code": 2250,
      "language_code": "fr",
      "device": "desktop",
      "os": "windows",
      "depth": 10
    }
  ]
}
```

The API documents costs and task statuses at both envelope and task levels. Record original ranks, item types, requested/effective settings and timestamp; never collapse other SERP items into organic. [Live Advanced contract](https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/).

## Missing inputs and gates

| ID | Required input | Present state |
|---|---|---|
| P1 | Named site/GSC property, owner permission and exact list of 20 FR queries. | Site requested; not supplied. No real corpus selected. |
| P2 | Connected official MCP/authentication route, account entitlement and permission for the pilot. | No callable connection or verified account. Never paste credentials into an issue, chat or fixture. |
| P3 | Approval of the 40-attempt scope and proposed 5 USD consumption ceiling; effective server/host retry policy reviewed. | Not authorized or runtime-verified. No paid call dispatched. |
| P4 | Private storage/retention/export authorization, effective no-filter configuration, delivered-body capture and reconciliation procedure. | Owner-approved location and rights missing. BYOK does not imply redistribution rights. |
| P5 | Frozen baseline packets, independent report-claim extraction/review, target support and per-task decisions from C1 H4/H6/H7/H8/H10. | Human evidence pending in #6; no gain score can be asserted. |
| P6 | Actual full delivery, task ID, provider status/cost and effective context for at least one approved real acquisition. | No acquisition performed; actual cost and returned coverage are unavailable, not zero. |

If a site's GSC data is used to propose queries, retain the exact property, observed window and raw query identities privately. Freeze the list before viewing external SERPs. Diversity may guide selection, but does not supply intent labels, pair labels or truth about competition.

## Sequential execution and capture

1. Complete P1-P4 and recheck the frozen server revision, endpoint, pricing and allowed device/OS settings. If the hosted server revision cannot be pinned, record that separately and requalify its tool schema; do not attribute the source SHA to it.
2. Prepare a label-free baseline packet from approved observations. Keep original source identity/windows, absence/error/partial states and input hashes.
3. Before each task, record a unique query/device attempt, exact request bytes/hash, approved scope and quoted reservation. Include unresolved reservations in remaining funds. Stop before the next task when a cost or delivery is unknown, a context differs, a warning reports dropped tasks or any configured ceiling would be exceeded.
4. Dispatch only one task once. Record UTC start/end, host/tool versions, warning blocks, delivered MCP content, extracted unfiltered JSON, capture SHA-256, envelope/task statuses, task ID, reported costs and requested/effective context. Retain incomplete/error delivery explicitly; do not resend an ambiguous POST.
5. Reconcile reported envelope cost with task cost and account evidence. A missing/nonfinite/negative/disagreeing cost, task error or altered source keeps the attempt unresolved for review. Never record a failed or absent response as zero cost.
6. Repeat only after a resolved acquisition under the same approved scope. A provider account limit or host approval requirement remains independent of the local worksheet.
7. Compare baseline-only and baseline-plus-SERP packets using independent blinded annotation/review and the C1 protocol. Match the query and locale/device capture context; keep current external observations separate from historical GSC windows. Current SERPs cannot establish a past traffic cause.
8. Decide by task from observed support, coverage, unsupported claims, omissions and justified action changes. A 40-acquisition technical pilot is not statistical proof of general quality.

Private attempt records must preserve source files, not only hashes. Retain unknown fields and hostile third-party text as untrusted evidence. No source publication is implied by this protocol.

## Connector decision

**Pending real pilot.** The official generic MCP may suffice for a supervised experiment, but the inspected source does not implement the monetary/attempt/replay controls required for an autonomous native audit.

A missing guard is a reason to restrict this experiment, not proof that a new connector improves diagnostics. If the supervised official route cannot preserve the required capture/control, first design a single bounded acquisition wrapper against the same approved task; do not route through an unrestricted sequence of MCP calls. Native tasks 2-4 require a documented missing capability and their own transport/ledger/parser tests before use. Labs and backlinks remain separate qualifications; no provider feature or default is enabled by this source review.

## Verification record

- Read the official source at the pinned revision, including schema, request, middleware, field filtering and result serialization.
- Verified the France row and SHA-256 of the public CSV.
- Checked the synthetic request's JSON syntax and single-task/full-schema parameters locally; this does not execute the MCP or provider.
- Documentation-only change: no production code, dependencies, default tool catalogue or global configuration changed.
- No synthetic output is presented as a real task response or account test.

Skills used: flow-lean, superpowers:executing-plans
