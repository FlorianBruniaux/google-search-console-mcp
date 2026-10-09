# Local crawl-log audit

Source changes after 1.4.0 add `crawl_log_audit` to the shared registry/CLI in the technical family. It reads one explicitly selected regular local access-log file. [Apache common/combined formats](https://httpd.apache.org/docs/2.4/logs.html) require a timestamp offset. Custom virtual-host, compressed and JSON profiles are unsupported. Logs are client-supplied, untrusted observations; these two profiles do not prove the hostname association.

```sh
gsc-cli crawl-log-audit --log-path /absolute/path/access.log \
  --site sc-domain:example.com --profile combined --meta
```

Default limits are 2 MiB actually consumed, 20000 considered lines, 8192 bytes per line, 1000 retained distinct path hashes and 50 displayed paths. Configurable maxima are 10 MiB, 100000 lines, 10000 paths and 100 displayed paths. The parser drains long lines incrementally within the byte cap and never parses their fragments as new records. Limit hits, invalid/excluded lines and omitted paths remain visible. The digest covers consumed bytes, not unread bytes; file size at open and changes during reading are separate observations. No contiguous-day or whole-site coverage is inferred from the oldest/newest timestamp.

Default output excludes IPs, users, referrers, queries, raw lines and readable paths. `include_paths=True` explicitly reveals path/origin strings after query stripping; they can still be sensitive and remain untrusted. Encoded path case/bytes are preserved. The hash includes the declared site, origin and path, so absolute request origins and relative paths are not silently joined. Out-of-scope absolute targets are excluded. Common/combined logs have no hostname column: confirm file ownership/single-site scope before use, and do not feed a merged multi-host file as one verified inventory.

User-Agent groups are declared labels. `verify_googlebot=True` makes one fixed HTTPS request to Google's [published common-crawler ranges](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests), capped at 262144 decoded bytes and 5000 prefixes. It retains retrieval time and registry hash, never IPs. `in_current_google_ranges` means membership in that retrieved list, not proof of historical bot identity. A nonmatching address or failed registry remains distinct. Reverse DNS alone is never accepted, and this implementation makes no reverse/forward DNS calls. Other crawlers stay declared; the tool does not execute arbitrary verification plugins.

Observed HTTP requests/errors do not prove indexing, Google citations, current server state or complete crawler activity. The optional verification failure does not invalidate unrelated parsed log observations. This tool neither persists a normalized copy nor uploads, decompresses, crawls or joins inventories. Caller originals are unchanged; there is no generated-file retention or automatic deletion. Use the shared `crawl-log-audit` skill for a bounded read-only report. Tests use local synthetic logs and mocked registry responses, not authenticated live requests.
