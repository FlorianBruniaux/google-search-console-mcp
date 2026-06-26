# Changelog

## [0.9.0] - 2026-06-26

54 tools (+4), 518 tests (+51). Wave B de la seconde intégration `claude-seo` (MIT uniquement).

### Added

**Content : `preload_audit`**

- `preload_audit(url)` : fetch via `safe_httpx_get` (retourne le `httpx.Response` complet, donc headers inclus, SSRF-safe). Détecte : blocs `<script type="speculationrules">` parsés en JSON pour les actions `prefetch`/`prerender`, header HTTP `Speculation-Rules` (Chrome 122+), `<link rel="preload">` avec extraction des attributs `as`/`href`/`fetchpriority`, `<link rel="prerender">` déprécié (sunset Chrome 120), bloqueur bfcache `cache-control: no-store`. Génère une liste d'issues avec sévérité (`high`/`medium`/`low`) et `check`. Verdicts : `optimised` (prefetch+prerender + pas de bfcache killer) | `improvements_available` (règles présentes mais issues) | `not_implemented` (aucune Speculation Rules) | `fetch_error`.

**CrUX : `crux_lcp_subparts`**

- `crux_lcp_subparts(url, form_factor="PHONE")` : même endpoint CrUX que `crux_page_vitals`, requête 5 métriques simultanément (LCP global + 4 subparts). Retourne `lcp_p75_ms`, `lcp_rating`, et `subparts` : `ttfb_ms`, `resource_load_delay_ms`, `resource_load_duration_ms`, `render_delay_ms`, `dominant_phase` (nom court du subpart avec la valeur p75 la plus élevée). Clé API absente = `verdict="missing_key"` (pas de RuntimeError, contrairement à `crux_page_vitals`). Verdicts : `good` | `needs_improvement` | `poor` | `not_enough_data` | `missing_key` | `fetch_error`.

**Indexing : `indexnow_submit`**

- `indexnow_submit(site, key, urls)` : POST vers `https://api.indexnow.org/indexnow`. Protocole open source, consommé par Bing, Yandex, Seznam, Naver (pas Google). `validate_url_strict` sur chaque URL avant envoi (SSRF-safe), URLs invalides comptées dans `skipped_invalid`. Host extrait du paramètre `site` via `urlparse`. `keyLocation` dérivé automatiquement : `{site}/{key}.txt`. Sans `@with_retry` (pas une API Google). HTTP 200/202 = `ok` si aucun skip, `partial` si skips ; autres codes = `error`. Verdicts : `ok` | `partial` | `error`.

**SEO : `parasite_risk`**

- `parasite_risk(site, urls)` : analyse pure de chemins URL, sans fetch HTTP. Détecte les patterns de la politique Google du 2024-11-19 sur le site-reputation abuse. Trois niveaux de risque par URL : high (`/sponsored/`, `/affiliate/`, `/partner/`, `/brand-studio/`, `/paid-content/`, `/native-advertising/`, sections commerce produit `best-deals/top-picks`), medium (`/advisor/`, `/underscored/`, `/select/`, `/commerce/` d'après Forbes Advisor / CNN Underscored / WSJ), low (query params `?ref=`, `?aff=`, `?partner=`). `site_risk` = risque maximum sur toutes les URLs. Verdicts : `clean` | `at_risk` | `high_risk`. Pas d'auth requise. Adapté de `claude-seo` (agricidaniel, MIT).

### Changed

- `registry.py` : import + enregistrement des 4 nouveaux tools. Docstring : 50 → 54 tools.
- `properties.py` : `_ALL_TOOLS` += 4 entrées. Docstring `get_capabilities` : 50 → 54.
- `tests/test_registry.py` et `tests/test_properties.py` : compteurs 50 → 54.
- `README.md` : badge tests 467 → 518, comptes tools 50 → 54 (intro, section Tools, CLI, feature set), 4 nouvelles lignes dans le tableau.
- `docs/machine-readable/llms.txt` : module map complété pour les 4 nouveaux tools, comptes 50 → 54 et 467 → 518, patch points ajoutés.

### Tool count

50 → 54 tools. Test count : 467 → 518.

## [0.8.0] - 2026-06-26

50 tools (+3), 467 tests (+38). Wave A de la seconde intégration `claude-seo` (MIT uniquement).

### Added

**Content : 3 nouveaux tools sans auth Google**

- `content_quality(url)` : fetch via `safe_fetch_html` + extraction du texte visible (stdlib `html.parser`, skip des blocs script/style/nav/footer). Score quatre axes : filler phrases (liste MIT de `claude-seo`, `_AI_PATTERNS` CC BY-SA 4.0 volontairement exclu), densité informationnelle (entités nommées + nombres pour 100 tokens), répétition de bigrammes, contenu thin (<300 tokens). Score global pondéré (filler 35%, densité 35%, répétition 20%, longueur 10%). Flags : `filler`, `low-density`, `repetitive`, `thin-content`. Verdicts : `good` | `needs_work` | `thin_content` | `fetch_error`.
- `hreflang_audit(url)` : fetch + `_MetaParser` stdlib. Vérifie le self-referencing tag, la présence d'`x-default`, les codes ISO 639-1 (détecte `jp`→`ja`, `eng`→`en` à trois lettres), les régions ISO 3166-1 Alpha-2 (détecte `UK`→`GB`), la cohérence de protocole HTTP/HTTPS sur le set d'alternates. Audit de la page cible uniquement, les return tags bidirectionnels nécessitent un fetch séparé. Verdicts : `valid` | `issues_found` | `no_hreflang` | `fetch_error`.
- `page_technical_audit(url)` : `validate_url_strict` + `httpx.Client(follow_redirects=False)`. Audite : longueur du title (30-60), longueur de la meta description (50-160), directive meta robots (`noindex` = criticité haute), présence et cohérence du canonical, viewport, attribut `lang` sur `<html>`, trois security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`), détection de redirect (3xx + cible), accès Googlebot en robots.txt (fetch via `safe_fetch_html` + parse via `urllib.robotparser.parse()` stdlib pour rester dans la couche SSRF). Verdicts : `healthy` | `issues_found` | `fetch_error`.
- `src/gsc_mcp/tools/content.py` : module dédié avec deux parsers stdlib (`_TextExtractor` et `_MetaParser`, héritant de `html.parser.HTMLParser`) et la constante `_FILLER_PHRASES` (35 patterns, adaptés de `claude-seo`, MIT, `agricidaniel`).

### Changed

- `registry.py` : import + enregistrement des 3 nouveaux tools (`content_quality`, `hreflang_audit`, `page_technical_audit`). Docstring : 47 → 50 tools.
- `properties.py` : `_ALL_TOOLS` += 3 entrées. Docstring `get_capabilities` : 47 → 50.
- `README.md` : badge tests 429 → 467, comptes tools 47 → 50 (intro, section Tools, CLI, paragraphe feature set), nouvelle famille "Content" dans le tableau.
- `docs/machine-readable/llms.txt` : module map complété pour `content.py`, comptes 47 → 50 et 429 → 467, patch points de test ajoutés.

### Tool count

47 → 50 tools. Test count : 429 → 467.

## [0.7.0] - 2026-06-26

47 tools (+4), 429 tests (+147). Intégration sélective d'assets MIT de `AgriciDaniel/claude-seo`.

### Added

**Sécurité : module SSRF unifié**

- `src/gsc_mcp/url_safety.py` : protection SSRF et DNS-rebinding centralisée. Bloque les IPs privées/loopback/réservées, l'IPv4 obfusqué (décimal, hexadécimal, octal, FQDN avec trailing dot), les endpoints de métadonnées cloud (AWS IMDS `169.254.169.254`, Azure `169.254.169.254/metadata`, GCP `metadata.google.internal`, Oracle, Alibaba). DNS-pinning via patch de `socket.getaddrinfo` sous lock pour sécuriser les redirections. API publique : `validate_url()`, `validate_url_strict()`, `safe_httpx_get()`, `safe_fetch_html()`. Remplace les guards ad-hoc présents dans `technical.py` et `sitemaps.py`. Adapté de `claude-seo` (agricidaniel, MIT).

**Technical : génération JSON-LD**

- `schema_generate(schema_type, ...)` : génère un bloc JSON-LD Schema.org pour quatre types à fort impact SEO. `reservation` (FoodEstablishmentReservation avec provider, start_time, party_size, customer), `order_action` (OrderAction avec merchant, order_url, delivery methods), `discussion` (DiscussionForumPosting avec headline, author, url, date_published, comment_count optionnel), `profile` (ProfilePage avec mainEntity Person, sameAs, knowsAbout, worksFor). Aucun appel réseau, aucune auth requise. Adapté de `claude-seo` (agricidaniel, MIT).

**Drift monitoring : 3 nouveaux tools**

- `drift_baseline(url, with_cwv)` : capture un snapshot SEO d'une URL (title, meta description, robots, canonical, H1-H3, JSON-LD, OpenGraph, status HTTP, SHA-256 du HTML et des schemas). Stocké en SQLite via `platformdirs.user_data_dir("gsc-mcp")/drift/baselines.db` (WAL mode). CWV optionnel si `CRUX_API_KEY` est configuré.
- `drift_compare(url, with_cwv)` : fetch live puis applique 17 règles de diff (méthodologie Dan Colta, MIT) : 8 CRITICAL (changement de title, H1, canonical, meta robots, suppression de schema, perte de status 200, régression LCP/CLS), 6 WARNING (ajout/suppression H2-H3, modification meta description, ajout noindex, dégradation INP), 3 INFO (modification OpenGraph, ajout schema, variation de longueur HTML > 20%). Verdict global : `no_drift` | `drift_detected`.
- `drift_history(url, limit)` : liste les comparaisons stockées pour une URL avec le résumé des findings par run.

**Documentation SEO sourcée**

- `docs/seo-knowledge/comparison-rules.md` : 17 règles de drift avec seuils et sévérités. Source : Dan Colta (MIT).
- `docs/seo-knowledge/cwv-thresholds.md` : seuils LCP/INP/CLS/FCP/TTFB avec méthodologie de scoring (INP remplace FID).
- `docs/seo-knowledge/local-seo-signals.md` : signaux 2026 Whitespark/BrightLocal/Sterling Sky pour le SEO local et l'AI search.
- `docs/seo-knowledge/serp-overlap-methodology.md` : algorithme de clustering par overlap top-10 (Lutfiya Miller).

**Attribution**

- `NOTICE` : copyright MIT de `claude-seo` (Copyright (c) 2026 agricidaniel), contribution de Dan Colta, liste des assets portés, exclusions explicites (CC BY-SA word lists).
- `README.md` : section Credits pointant vers `github.com/AgriciDaniel/claude-seo`.

### Changed

- `technical.py` : `_reject_ssrf` interne remplacé par `url_safety.validate_url_strict`. Trois annotations `Optional[list]` corrigées en `Optional[list[str]]` pour la compatibilité CLI.
- `sitemaps.py` : origin-check des URLs enfant rebranché sur `url_safety.validate_url_strict`.
- `cli.py` : `_type_kind()` étend la détection aux annotations `typing.Optional[X]` (= `typing.Union[X, None]`) et `bool`. `_build_subparser()` gère le cas `bool` avec `store_true`/`store_false`. Corrigeait un `sys.exit(1)` silencieux qui cassait la construction des 47 parsers.
- `registry.py` + `properties.py` : 4 nouveaux tools enregistrés (`schema_generate`, `drift_baseline`, `drift_compare`, `drift_history`).

### Fixed

- CLI : 56 tests en échec causés par `_type_kind()` qui ne gérait pas `typing.Optional` ni `bool` (annotations des tools drift et schema_generate).
- Tests `test_technical.py` + `test_sitemap_audit.py` : cible de mock DNS corrigée (`gsc_mcp.url_safety.socket.getaddrinfo` au lieu de `gsc_mcp.tools.technical.socket.getaddrinfo`).
- `test_technical.py` : assertion SSRF corrigée (`"192.168.1.1" in result["error"]` au lieu de `"Blocked"`).
- `test_properties.py` + `test_registry.py` : compteurs hardcodés 43 → 47.

### Tool count

43 → 47 tools. Test count : 282 → 429.

## [0.6.2] - 2026-06-25

### Added

- README: "What's New" section summarizing v0.6.0 and v0.6.1 highlights for users landing on the repo
- README: Troubleshooting section covering the 6 most common setup issues (auth, GA4, CrUX, Indexing API quota, uvx launch)

## [0.6.1] - 2026-06-24

Refactor interne et corrections sans nouveau tool.

### Fixed

- Entrypoint `gsc-mcp-tools` manquant dans `pyproject.toml` : `uvx gsc-mcp-tools` échouait avec "An executable named gsc-mcp-tools is not provided by package gsc-mcp-tools". Les deux noms (`gsc-mcp` et `gsc-mcp-tools`) pointent maintenant sur le même `gsc_mcp.server:main`
- README : badge tests corrigé (286 → 282), compteur dev section corrigé (222+ → 282), tableau détaillé complété avec les 4 tools manquants (`sitemap_audit`, `crux_page_vitals`, `crux_history`, `schema_validate`), descriptions Cross traduites de FR en EN

### Changed

- **Ponytail refactor** (complexité sans valeur supprimée) :
  - `auth.py` : helper `_ga4_creds()` extrait pour éliminer la duplication entre `get_ga4_service` et `get_alpha_ga4_service`
  - `analytics.py` : `_SEARCH_TYPES` déplacé en variable locale dans `search_type_breakdown` (pas d'autres usages)
  - `seo.py` : helper `_two_periods(days)` ajouté pour déduplication du calcul de dates dans `traffic_drops` et `seo_lost_queries`
  - `sitemaps.py` : `DefusedXmlException` ajouté au `except` interne de `_fetch_xml`, bloc `try/except` externe supprimé
  - `indexing.py` : `_submit_batch_impl` fusionné dans `submit_batch`, couche de délégation supprimée
  - `cross.py` : dicts parallèles remplacés par de l'arithmétique directe dans la renormalisation de `page_health_score`
- **Tests** : `test_seo_v2.py` et `test_sitemaps_v2.py` fusionnés dans `test_seo.py` et `test_sitemaps.py` respectivement, puis supprimés. `test_scaffold.py` supprimé (couvert par conftest et imports)
- Test count : 268 → 282

## [0.6.0] - 2026-06-24

7 nouveaux tools, 43 tools au total, 268 tests.

### Added

**Analytics GSC : nouvelles variations search type**

- `discover_performance(site, days, limit)` : performances Google Discover par page. Utilise `"type": "discover"` dans le corps de requête. La dimension `query` n'est pas supportée par Discover, seul `page` est retourné. Trié par impressions décroissantes.
- `news_performance(site, days, limit)` : identique à `discover_performance` mais pour Google News (`"type": "googleNews"`).
- `search_type_breakdown(site, url, days)` : 5 appels séquentiels à `_fetch_rows` (web, discover, googleNews, image, video), agrège clicks et impressions par type. Paramètre `url` optionnel pour filtrer sur une page spécifique.
- `ai_overviews_impact(site, days, limit)` : requête avec `"dimensions": ["query", "searchAppearance"]` et `"dataState": "all"`. Retourne un dict `{"error": "AI_OVERVIEWS_NOT_AVAILABLE"}` sur HttpError 400/403 (propriétés sans données AI Overviews) sans lever d'exception. Les erreurs 500+ restent remontées.

**Cross GSC+GA4 : outils composites**

- `page_health_score(site, url, property_id, hostname, country)` : score composite 0-100 combinant 4 sources. GSC (30 pts via `inspect_url`), GA4 (25 pts via `ga4_page_performance`), CrUX (25 pts via `crux_page_vitals`, LCP+INP+CLS), et schema (20 pts via `schema_validate`). Chaque composant est isolé dans un `try/except RuntimeError` : si une source est absente (credentials manquants), ses points sont 0 et le score est renormalisé sur les sources disponibles.
- `content_brief(site, page_url, days, property_id)` : intelligence éditoriale par page. Filtre les requêtes GSC sur `page_url` (normalisation via `_normalize_url`), trie par clicks, extrait les requêtes "question" (who/what/when/where/why/how) depuis la liste complète filtrée. Enrichit avec `ga4_page_performance` (sessions, engagement_rate) en dégradation gracieuse si GA4 est absent.

**GA4 : funnel via v1alpha**

- `ga4_funnel(steps, start_date, end_date, property_id)` : rapport de funnel multi-étapes via `AlphaAnalyticsDataClient.run_funnel_report()`. Validation stricte : moins de 2 étapes retourne `{"error": "INVALID_STEPS"}`. Chaque étape est un dict `{"name": str, "event": str}`. Taux de conversion par étape relatif à l'étape 1 (qui est toujours `null`). Nouveau getter `get_alpha_ga4_service()` dans `auth.py`, même scope et token que la beta.

### Changed

- Tool count : 36 -> 43
- Test count : 222 -> 268
- `get_capabilities` docstring : "36" -> "43", `_ALL_TOOLS` étendu avec les 7 nouveaux tools

## [0.5.0] - 2026-06-23

4 nouveaux tools, filtres hostname/country sur tous les tools GA4, et 55 nouveaux tests. 36 tools au total, 222 tests.

### Added

**GA4 : filtres hostname et country (tools existants)**

- `_build_dimension_filter(hostname, country, base_filter)` dans `ga4.py` : construit un `FilterExpression` seul ou un AND group (via `FilterExpressionList`) selon le nombre de filtres actifs. Backward-compatible : avec `None, None`, le comportement est identique à avant
- Paramètres `hostname: str | None = None` et `country: str | None = None` ajoutés à `ga4_organic_landing_pages`, `ga4_traffic_sources`, `ga4_page_performance`, `ga4_user_behavior`, `ga4_conversion_funnel`
- Paramètre `hostname: str | None = None` ajouté à `ga4_realtime` (`country` non disponible sur `runRealtimeReport`)
- Mêmes paramètres propagés à `traffic_health_check` et `page_analysis` (passés à `ga4_organic_landing_pages` en interne)
- 20+ nouveaux tests dans `test_ga4.py` et correction de `test_pa_meta` dans `test_cross.py`

**CrUX : Core Web Vitals réels (nouveaux tools)**

- `crux_page_vitals(url, form_factor)` : interroge le Chrome UX Report API (`:queryRecord`). Retourne LCP, INP, CLS, FCP, TTFB avec ratings good/needs_improvement/poor, percentiles p75, et un verdict global `good`/`needs_improvement`/`poor`/`not_enough_data`. Nécessite `CRUX_API_KEY`
- `crux_history(url, form_factor)` : séries temporelles hebdomadaires via `:queryHistoryRecord`. Retourne jusqu'à 25 semaines de p75 par métrique pour tracker les régressions CWV
- `CRUX_API_KEY` : variable d'env distincte de l'auth GSC (Google API Key simple, pas service account). La Chrome UX Report API doit être activée dans le projet GCP
- Nouvelle dépendance : `httpx>=0.27.0`
- 16 nouveaux tests dans `tests/test_crux.py`

**Sitemaps : audit de couverture (nouveau tool)**

- `sitemap_audit(site, sitemap_url)` : fetch un sitemap (ou sitemap index) via httpx, parse les URLs avec `defusedxml.ElementTree` (prévient XXE et billion-laughs), cross-référence contre 90 jours de GSC via `get_search_analytics`. Gère les sitemap index avec une récursion d'un niveau. Verdicts : `empty` | `fetch_error` | `partial` (>20% URLs absentes de GSC) | `healthy`
- Protection SSRF : les child sitemaps d'un sitemap index sont validés contre l'origin du sitemap parent (`follow_redirects=False`)
- Nouvelle dépendance : `defusedxml>=0.7.1`
- 7 nouveaux tests dans `tests/test_sitemap_audit.py`

**Technical : validation JSON-LD (nouveau tool)**

- `schema_validate(url)` : fetch n'importe quelle URL publique via httpx, extrait tous les blocs `<script type="application/ld+json">` via `html.parser` (stdlib, pas de dépendance externe), valide les champs requis par type (Article, LocalBusiness, FAQPage, Product, WebSite, BreadcrumbList, SoftwareApplication...), et suggère des schemas manquants selon les patterns d'URL (/faq → FAQPage, /blog/ → BlogPosting, etc.). Verdicts : `healthy` | `missing_schemas` | `invalid_schemas` | `fetch_error`. Ne nécessite pas d'auth
- 15 nouveaux tests dans `tests/test_technical.py`

### Changed

- Tool count : 32 → 36
- Test count : 167 → 222
- `get_capabilities` docstring : "32" → "36", `_ALL_TOOLS` étendu avec les 4 nouveaux tools
- `pyproject.toml` description mise à jour pour refléter les 36 tools et les nouvelles catégories

## [0.4.2] - 2026-06-22

### Added

- Tous les tools GA4 (`ga4_organic_landing_pages`, `ga4_traffic_sources`, `ga4_page_performance`, `ga4_realtime`, `ga4_user_behavior`, `ga4_conversion_funnel`) et les tools cross (`traffic_health_check`, `page_analysis`) acceptent un paramètre optionnel `property_id: str = None`. Quand fourni, il override `GA4_PROPERTY_ID` sans modifier la config. Permet de requêter plusieurs properties GA4 depuis une seule instance MCP.
- `get_ga4_property_id(override=None)` dans `auth.py` : accepte un override direct, court-circuite la lecture de l'env var. Sans override, comportement identique à avant.
- 4 nouveaux tests : `test_get_ga4_property_id_override_takes_precedence`, `test_get_ga4_property_id_override_no_env_needed`, `test_thc_property_id_propagated`, `test_pa_property_id_propagated`

## [0.4.1] - 2026-06-22

Corrections de cohérence et consolidation interne : pas de nouveaux tools.

### Fixed

- `get_capabilities` retournait 18 tools sur les 32 réellement disponibles. Les 14 manquants (`analytics_anomalies`, `seo_striking_distance`, `seo_cannibalization`, `seo_lost_queries`, `sitemaps_delete`, `sitemaps_get`, 6 tools GA4, `traffic_health_check`, `page_analysis`) sont maintenant listés
- `inspect_url`, `batch_url_inspection`, `check_indexing_issues` appelaient `webmasters/v3`, qui n'expose pas `urlInspection`. Ces trois tools levaient une `AttributeError` au runtime sur chaque appel. Corrigé en passant sur `searchconsole/v1` (API qui expose la ressource `urlInspection`)
- `traffic_health_check` et `page_analysis` incluent maintenant un champ `note` dans leur réponse JSON pour avertir que GSC a un décalage de 3 jours vs GA4, les ratios sont donc approximatifs
- `ga4_organic_landing_pages` ajoute un champ `note` quand le nombre de résultats atteint la limite, signalant une troncature potentielle

### Changed

- Tous les tools GSC (analytics, SEO, sitemaps, properties) consolidés sur `searchconsole/v1`. Le client `webmasters/v3` (`get_gsc_service`) est supprimé de `auth.py`. `searchconsole/v1` expose les mêmes ressources `sites`, `searchanalytics`, `sitemaps` en plus de `urlInspection`

### Tests

- Couverture `quick_wins` améliorée : 4 nouveaux cas couvrant les pages à CTR zéro avec impressions suffisantes, l'exclusion sous le seuil d'impressions et l'exclusion des pages déjà au benchmark de CTR

## [0.4.0] - 2026-06-22

Phase 3: 2 tools cross-platform GSC+GA4, nouveau module `cross.py`.

### Added

- `traffic_health_check(site, days)`: compare les clics GSC agrégés avec les sessions organiques GA4 pour détecter les écarts de tracking. Retourne un statut parmi `no_gsc_data`, `tracking_gap` (ratio < 0.6), `filter_issue` (ratio > 1.3) ou `healthy`. GA4 interrogé avec `limit=10000` pour éviter les sous-comptages sur les gros sites
- `page_analysis(site, days, limit)`: jointure page par page entre GSC (dimensions=["page"]) et GA4 (landing pages organiques). Les pages présentes dans une seule source sont incluses avec les champs manquants à `None`. Chaque page reçoit un `opportunity_score = log10(impressions+1)*10 + engagement_rate*100 + log10(conversions+1)*20`, trié décroissant, tronqué à `limit`
- `_normalize_url(url)` helper interne: ramène URLs absolues (GSC) et paths GA4 au même chemin nu, sans scheme, host, query ni slash final, pour fiabiliser la jointure
- `engagement_rate` dérivé dans `cross.py` comme `engaged_sessions/sessions` (formule GA4 native), sans modifier la sortie de `ga4_organic_landing_pages`
- 24 nouveaux tests dans `tests/test_cross.py`, dont les boundaries 0.6 et 1.3 du ratio, les cas GSC-only, GA4-only, trailing slash et query string

### Changed

- Tool count: 30 vers 32

## [0.3.0] - 2026-06-22

Phase 2: 6 new GA4 tools, new dependency, new environment variable.

### Added

- `ga4_organic_landing_pages(start_date, end_date, limit)`: sessions, engaged sessions, bounce rate, average session duration, conversions and revenue for organic landing pages. Uses the `sessionMedium=organic` filter on `landingPagePlusQueryString`
- `ga4_traffic_sources(start_date, end_date)`: sessions and conversions broken down by channel group, source and medium
- `ga4_page_performance(start_date, end_date, page_path)`: 7 metrics per page path (page views, active users, average session duration, engagement rate, bounce rate, conversions, revenue). Optional `page_path` parameter adds a CONTAINS filter
- `ga4_realtime()`: active users right now, by screen name, country and device. No date range, uses `run_realtime_report` directly
- `ga4_user_behavior(start_date, end_date)`: single `batch_run_reports` call returning three breakdowns (by device, by country top 20, by user type new/returning)
- `ga4_conversion_funnel(start_date, end_date, event_name)`: two sequential `run_report` calls. First lists pages with conversions > 0; second lists events, optionally filtered by exact event name
- New dependency: `google-analytics-data>=0.18.0` (Google Analytics Data API v1beta, protobuf-based client)
- New environment variable: `GA4_PROPERTY_ID` (numeric property ID, e.g. `123456789`). Validated lazily on first GA4 tool call, never at startup. GSC-only users are not affected
- `get_ga4_service()` and `get_ga4_property_id()` in `auth.py`, reusing the same `_resolve_creds` path as GSC and Indexing clients

### Changed

- Tool count: 24 → 30

## [0.2.0] - 2026-06-22

Phase 1: 6 new tools, no new dependencies.

### Added

- `seo_striking_distance(site, days, min_impressions)`: queries in positions 8-15 sorted by impressions desc. Separate band from `quick_wins` (4-15), intended for queries one push away from page 1
- `seo_cannibalization(site, days, min_impressions)`: detects queries split across multiple pages using an HHI conflict score (`1 - sum(share²)`). Zero-click groups use uniform `1/n` fallback to avoid division by zero. Filters on per-query total impressions, not per-page
- `seo_lost_queries(site, days)`: flags queries with a click drop ≥ 80% vs the previous period, requiring at least 5 previous clicks. Iterates over the previous period to catch fully-vanished queries. Same two-window no-lag pattern as `traffic_drops`
- `analytics_anomalies(site, days, threshold)`: Z-score anomaly detection on daily clicks via `statistics.pstdev`. Returns `anomalies = []` when std is zero (constant or all-zero series) to handle low-traffic sites safely
- `sitemaps_delete(site, sitemap_url)`: deletes a sitemap with a safety check before any API call (URL must end with `.xml` or contain `/sitemap`, raises `ValueError` otherwise)
- `sitemaps_get(site, sitemap_url)`: fetches a single sitemap resource and normalises it to the same flat shape as `list_sitemaps` (warnings and errors coerced to int)
- 62 new tests (35 SEO, 15 sitemaps, 9 analytics anomalies): all mocked, no API calls

### Changed

- Tool count: 18 → 24

## [0.1.0] - 2026-06-20

Initial release.

### Added

- 18 MCP tools across 6 categories: meta, properties, analytics, SEO, inspection, indexing, sitemaps
- `submit_batch` using true HTTP multipart batch via `new_batch_http_request()`, chunked at 100 URLs per request. Avoids the late-binding closure bug with a `_make_callback(url)` factory pattern
- Dual OAuth scope architecture: separate clients for GSC (`auth/webmasters`) and Indexing API (`auth/indexing`), because the Indexing API rejects webmasters tokens
- OAuth flow with token stored as JSON (`google.oauth2.credentials.Credentials.to_json()`) instead of pickle
- Service Account support as an alternative to OAuth (set `GSC_SERVICE_ACCOUNT_PATH`)
- Exponential backoff retry on HTTP 429/500/502/503/504 via `with_retry()` decorator, no retry on 404
- In-memory quota tracker (`QuotaTracker`) with configurable limit and warn threshold (warns at 180/200 by default)
- `with_meta()` wrapper on all tool outputs: every response includes a `_meta` block with tool name and call parameters, so Claude has full context on what was fetched
- `quick_wins` tool scoring CTR opportunity vs benchmark by SERP position
- `check_indexing_issues` categorizing URLs into `not_indexed`, `robots_blocked`, `fetch_error`, `canonical_issue`, `indexed`
- `traffic_drops` diagnosing drops as `ranking_loss`, `ctr_collapse`, or `demand_decline`
- Full test suite: 52 tests, fully mocked, no Google API calls required
