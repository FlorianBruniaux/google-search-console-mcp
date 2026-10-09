# Local crawl-log validation, 2026-10-09

`crawl_log_audit` reads one explicitly selected regular common/combined access-log file. It bounds bytes, line length/count, retained paths and displayed rows. Default summaries omit IPs, users, referrers, queries, readable paths and raw lines. Site association remains caller-declared because these two profiles have no virtual-host field. Observed minimum/maximum UTC timestamps do not certify continuous coverage.

Local Python validation passes 1,886 tests. Fixtures cover timezone offsets, invalid months, partial lines, oversized records, path/line/byte caps, foreign absolute requests, file failures before network access, sensitive values, unavailable identities and current Google range membership. HTTP transports are mocked; no historical Google request or live account was authenticated. Membership in the current official address registry is distinct from verified identity at the log timestamp. Default parsing makes no network request.

Repository BM25 checks pass for 14 SEO skills on both host projections; the new log skill has F1 0.93 on its declared routing corpus. These checks establish routing and source parity, not native agent behavior or human SEO accuracy. No global index was edited.

Documentation checks pass 6 cases, distribution checks 29, translations pass, and Astro reports zero diagnostics across 51 files. The site builds 61 pages. Nine visual reference images change for the source catalogue count, from 89 to 90, and were inspected before regeneration. No local log is persisted or uploaded; inventory joins and custom/compressed profiles remain unsupported.
