# Versioned crawl inventory validation, 2026-10-09

The first snapshot schema uses the reviewed SiteOne adapter and adds exact caller-site ownership, all supported in-scope rows, source/configuration hashes, declared times, validation coverage and explicit unknown selection/timezone. The optional local SQLite store is immutable through its API, idempotent, quota-bound and private on POSIX. It has no automatic retention or original-export deletion. The store checksum detects accidental payload corruption; it does not authenticate an external collector.

Local Python validation passes 1,915 tests. Snapshot cases cover default no-write preview, all 73 public-fixture rows, Unicode/query/fragment identity, duplicate rows, scope exclusions, cross-site handles, count/byte quotas, confirmed cleanup, missing reads, symlink refusal, corruption and bounded pagination. Reconciliation cases cover zero versus missing/null, duplicate GSC keys, wrong dimensions/sites, malformed JSON and invalid metrics. Supplied reports are not a live Google check. Link records retain the existing producer's path aggregation and candidate/sample limits.

Repository routing passes 248 scenarios across 15 SEO targets for both host projections. The import target has F1 1.00 and the log target 0.67 after adding the import corpus. This measures routing only; native model behavior and expert SEO quality are unverified. No global cache/index was modified.

Site validation passes 6 documentation tests, 29 built-distribution tests, translation verification and 111 Chromium/macOS browser checks. Astro reports zero diagnostics and builds 61 pages. Source catalogue counts change to 94; the inspected homepage retains its layout. Nine number-related reference images were refreshed.

Unlighthouse remains unsupported pending an actual versioned export. No crawler runtime, authorized customer data, bot authentication, provider indexing or lab-versus-field equivalence is inferred from these fixtures.
