# Agent boundaries, 2026-10-09

The #39 pilot aligns the nine SEO role tool allowlists with their shared playbooks. Schema validation describes local field checks, not Google rich-result eligibility; striking distance retains the tool's 8..15 range.

The controlled workflow rejects a discovery property mismatch and selected URLs outside that GSC property. URL-prefix properties retain their origin/path scope; domain properties include subdomains. Credential-bearing, malformed and non-HTTP URLs are refused before downstream dispatch. These checks do not replace the tools' safe fetching or prove that discovery observations are authentic.

The run envelope retains a run identifier, exact property, selected URLs, configured page/concurrency/agent-call/source-byte limits and attempted host-agent calls. Every failed host-agent invocation counts. Source observations are shared as serialized discovery data; oversized synthesis input fails explicitly. Branches requiring a page are marked unavailable before invocation when no HTTP URL is selected. Optional failures and unknown indexing remain visible beside a separate evidence-review invocation and the unapproved draft.

Validation: 57 controlled-host and role/playbook checks pass. Fixtures verify missing-page skips, property mismatch, cross-site/credential URLs, failed-attempt accounting, source-byte failure and existing unknown/error preservation. These are Node host fixtures and Python structural checks. They do not execute a live agent or Google provider.

Remaining #39 gates: a native Claude/Codex host adapter, verified provider capabilities, an aggregate budget at the actual provider-call boundary, immutable acquired observations across all specialists, and human evaluation under #6. Sharing discovery in a prompt is not enforcement against repeated model tool calls. `model: sonnet` belongs only to Claude role files; there is no Codex model-alias projection or claim of native execution.
