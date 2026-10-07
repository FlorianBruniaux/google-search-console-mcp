# Example Prompts

Scenario-based conversation starters for the published 81-tool registry. Each file covers one use case with a progression from a first question to a deeper investigation.

Start with the first prompt in any file and replace `yourdomain.com` with your property or verified-site URL. Configure the required providers with the [installation guide](../docs/installation.md), [Google setup](../docs/google-setup.md) or [Bing setup](../docs/bing-setup.md).

## Scenarios

For a measured example, read the [Claude Code Ultimate Guide run](cc-guide-live-audit.md), recorded on 2026-10-07. It includes Google metrics, page checks, suggested actions and a shareable [MCP trace](evidence/2026-10-07-cc-guide.json). No site changes or ranking improvements are claimed.

| File | Providers | Use case | Depth |
|---|---|---|---|
| [quick-audit.md](quick-audit.md) | Google, optional Bing | Site health check at a glance | Quick |
| [google-bing-comparison.md](google-bing-comparison.md) | Google + Bing | Compare engines without mixing incompatible metrics | Intermediate |
| [full-audit.md](full-audit.md) | Google, optional Bing and GA4 | Complete audit with P0/P1/P2 action plan | Complete |
| [keyword-opportunities.md](keyword-opportunities.md) | Google + supported Bing analyses | Find measured ranking opportunities | Intermediate |
| [page-deep-dive.md](page-deep-dive.md) | Google, optional Bing, CrUX | Diagnose a single URL | Intermediate |
| [traffic-drop.md](traffic-drop.md) | Google | Investigate a traffic drop across exact adjacent periods | Intermediate |
| [indexing-issues.md](indexing-issues.md) | Google | Inspect indexing evidence and eligible submissions | Intermediate |
| [content-brief.md](content-brief.md) | Google, optional GA4 and CrUX | Build a brief from observed search data | Intermediate |

## How to use these

Copy a prompt into Claude, Codex or another MCP-compatible client. Each file contains a starting question, evidence-preserving follow-ups and explicit boundaries for writes.

The prompts work as-is. You don't need to know which API tool runs behind each question.

Read-only analysis does not authorize a write. Before a sitemap, URL, feed or IndexNow mutation, the assistant must name the exact tool and target, report the number of affected items, and wait for explicit confirmation. An accepted submission proves neither crawl nor indexation.
