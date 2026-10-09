# Versioned local crawl inventories

Source implementation after PyPI 1.4.0. Supported producer: the reviewed `siteone-json-v1` exporter. No crawler, browser, network connection or upload is started by these tools.

## Import and ownership

`crawl_snapshot_import(report_json, site, persist=False)` validates a supplied JSON string and returns an inventory envelope without writing. Set `persist=True` explicitly to store accepted in-scope rows locally. The exact caller-selected property owns the snapshot; common input associated with two properties receives two distinct IDs. That association is declared by the caller, not authenticated by a provider.

Schema `gsc-crawl-snapshot-v1` retains the producer/version, source byte hash, configuration hash/options, declared collection time, validation counts, source errors/notices and score basis. Selection and source execution timezone remain unknown. The snapshot ID includes the schema, adapter, exact site and source hash. Same bytes produce the same ID; modified bytes/options or owner produce a different ID. Original raw URL strings, query order, fragments, Unicode and duplicates are retained. Foreign URLs are excluded and counted.

All accepted rows can be retained, up to the adapter's 5,000-row and 2 MiB input limits. Preview summaries omit row details; `crawl_snapshot_read(site, snapshot_id, offset=0, limit=50)` returns bounded pages, at most 100 rows per call, with the complete source envelope and pagination. Duplicate raw URLs remain visible. Unsupported extra fields and crawler command/hostname are withheld, following the reviewed adapter. Imported statuses, strings and scores are untrusted data; no page instruction is executed. Scores are third-party rules, not ranking impact.

## Local storage and cleanup

The dedicated SQLite store is `platformdirs.user_data_dir("gsc-mcp")/crawl-snapshots/inventory.sqlite3`, with directory mode 0700 and file mode 0600 on POSIX. It contains imported URL queries and other supported producer observations, so use authorized exports. Credentials in recognized URL fields are rejected by the existing adapter; this is not a general secret scanner.

Retention is explicit. The store refuses a new write above 64 snapshots or 16 MiB of retained serialized payloads. It does not evict old data or delete the source export. The byte quota bounds payloads, not filesystem overhead or backup copies. Repeated imports reuse the first import timestamp and do not consume another slot. IDs are opaque hashes, not file paths.

`crawl_snapshot_delete(site, snapshot_id, confirm=False)` requires explicit `confirm=True` before deleting the matching local record. The exact owner is required. No wildcard purge, original-file deletion or provider mutation occurs. Missing reads do not initialize a store. SQL deletion is not a guarantee of forensic erasure from storage or backups.

## Reconciliation

`crawl_snapshot_join(site, snapshot_id, search_report_json=None, link_report_json=None, offset=0, limit=50)` accepts bounded caller-supplied results from `get_search_analytics` or `get_advanced_search_analytics` with page-only dimensions, the exact property and an explicit requested date range. It matches raw URL strings without normalization. Same-path parameter variations stay separate; duplicate search keys are ambiguous and are not summed. Explicit zero counts remain zero; missing rows or metrics stay unavailable. Legacy CTR/position zero with zero or absent impressions is unavailable.

Optional `link_equity_map` input preserves that tool's path-only aggregation, selected candidate lists and crawled/failed page counts. Matching a returned URL does not undo its path aggregation. Absence from a bounded candidate list does not prove a page is orphaned. Its exact collection time and observed search window are unavailable in the current output contract.

Incoming reports are caller-supplied. Their `_meta` fields are validated for consistency but do not authenticate provider access. Search requested windows and crawl declared timestamps remain separate observations; the join cannot assert simultaneous collection. No Google indexing state or whole-site completeness is inferred from clicks, missing rows, crawls or link candidates.

## Example

In an MCP client, supply your authorized export as `report_json` and the exact property to `crawl_snapshot_import`, first with default preview, then with `persist=True`. Keep its `snapshot_id`; use it in `crawl_snapshot_read` or `crawl_snapshot_join`. Read small pages before requesting further detail.

For CLI imports, `report_json` is the JSON string, not a filename. Existing `crawl_import_preview` remains an in-memory first check with at most 50 displayed rows. There is no implicit disk read of a caller-supplied path.

Unlighthouse is unsupported until an actual versioned export is reviewed. No lab metrics stand in for missing field metrics or INP. The licensed public SiteOne fixture validates export compatibility, not a fresh crawl or site correctness.
