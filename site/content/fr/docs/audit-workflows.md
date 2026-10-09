---
title: "Audits à périmètre borné"
description: "Comparer des fenêtres Google explicites et observer les destinations des liens internes avec leurs limites de couverture."
lang: fr
lastUpdated: 2026-10-09
canonicalEnglish: /docs/audit-workflows/
---

`search_change_breakdown` et `link_targets_audit` sont inclus dans `gsc-mcp-tools==1.3.0`, qui expose 85 outils. Suivez les [instructions d’installation](/fr/docs/installation/). Les exemples ci-dessous sont des fragments synthétiques explicatifs, sans appel réel à Google ou au réseau.

La version 1.4.0 inclut la correction des apparences IA, le contrat/budget de rapport, la référence hebdomadaire et la prévisualisation de crawl ci-dessous. Elle expose 89 outils ; suivez l’[installation](/fr/docs/installation/) pour mettre à jour le paquet.

## Les apparences de recherche ne prouvent pas une exposition IA

`ai_overviews_impact(site, days=28, limit=100)` conserve son nom public mais lit les lignes génériques Web `searchAppearance`. Il demande cette dimension seule, conformément à la documentation Google ; il ne fournit pas de comparaison d’exposition IA par requête. Les valeurs d’apparence reçues sont des observations, sans règle vérifiée identifiant les AI Overviews.

`source_scope` vaut `web_search_appearance` ; `ai_exposure.status` vaut `unavailable` et `ai_exposure.verification`, `unverified`. Une réponse réussie distingue les apparences observées d’une réponse vide. HTTP 400 conserve l’alias d’erreur existant et signale une requête invalide ou non prise en charge ; HTTP 403 signale un accès refusé. Ni une réponse vide ni ces erreurs ne prouvent une présence ou une absence IA. Les valeurs demandées avec `dataState=all` peuvent changer pendant leur finalisation. Le rapport ne calcule pas de perte de clics causée par l’IA.

Sur la branche source après 1.4.0, les métriques d’apparence distinguent les zéros explicites des valeurs absentes, nulles ou invalides. Lignes partielles, dimension manquante, conteneur malformé, réponse vide et refus HTTP restent distincts. La propriété exacte et les dates demandées accompagnent la réponse ; la fenêtre observée reste inconnue sans contrôle daté. Les bornes `days` (1..366) et `limit` (1..25000) sont vérifiées avant l’accès.

Consultez les [consignes Google sur les apparences](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data#getting_search_appearance_data) et les [limites de mesure des fonctionnalités IA](https://developers.google.com/search/docs/appearance/ai-features#measuring-the-performance-of-your-site). Les tests utilisent des réponses synthétiques ; ils ne vérifient pas les capacités d’une propriété réelle.

## Comparer des fenêtres Google explicites

`search_change_breakdown` exige la propriété GSC exacte et des dates inclusives ordonnées, sans chevauchement et de même durée. Cet outil prend uniquement Google en charge.

```python
search_change_breakdown(
    site="sc-domain:example.com",
    baseline_start="2026-09-01", baseline_end="2026-09-07",
    comparison_start="2026-09-08", comparison_end="2026-09-14",
    dimensions=["page", "query"],
    filters=[{"dimension": "country", "operator": "equals", "expression": "fra"}],
    search_type="web", data_state="final", aggregation_type="auto",
    row_limit=1000, max_requests=20, limit=50,
)
```

La même requête via la CLI conserve les métadonnées avec `--meta` :

```bash
gsc-cli search-change-breakdown --site sc-domain:example.com \
  --baseline-start 2026-09-01 --baseline-end 2026-09-07 \
  --comparison-start 2026-09-08 --comparison-end 2026-09-14 \
  --dimensions page --dimensions query \
  --filters '[{"dimension":"country","operator":"equals","expression":"fra"}]' \
  --search-type web --data-state final --aggregation-type auto \
  --row-limit 1000 --max-requests 20 --limit 50 --meta
```

Sans `dimensions`, les vues page, query, country et device sont indépendantes. Les filtres forment un groupe AND avec `dimension`, `operator` et `expression`. Les dimensions de filtre acceptées sont ces quatre valeurs et `searchAppearance` ; les opérateurs sont `equals`, `notEquals`, `contains`, `notContains`, `includingRegex` et `excludingRegex`. `search_type` accepte web, image, video ou news ; `data_state` accepte final ou all. Un regroupement ou filtre par page exige auto ; sinon l’agrégation accepte aussi byProperty et byPage.

`row_limit` borne les lignes récupérées par dimension et période (1..100000), `limit` les lignes affichées par section (1..1000). Le minimum de `max_requests` vaut 4 plus deux fois le nombre de dimensions, avec un maximum de 100. Ce budget compte les tentatives fournisseur, y compris les échecs. Les agrégats et sondes par date précèdent les dimensions ; les pages restantes sont récupérées à tour de rôle, sans retry caché ni sonde finale supplémentaire.

Une requête synthétique avec 100 clics avant et 70 après donne ce fragment :

```json
{
  "breakdowns": {
    "query": {
      "matched": [{"key": "example query", "baseline": {"clicks": 100}, "comparison": {"clicks": 70}, "delta": {"clicks": -30}}],
      "comparison": {"comparable": true, "reason": null, "scope": "observed matched rows; equal requested windows do not prove complete equal coverage"}
    }
  }
}
```

Les lignes complètes contiennent aussi impressions, CTR, position et raisons d’indisponibilité. Une valeur manquante, invalide ou indisponible reste null ; un zéro mesuré reste zéro. Une ligne présente dans une seule période conserve null pour l’autre observation et son delta. Les clés fournisseur sont jointes exactement, sans normaliser les URL. Le CTR est calculé depuis les comptes ; la position reste la moyenne de la ligne fournisseur, sans moyenne entre segments.

`baseline_totals` vient des requêtes sans dimension. Vérifiez `periods`, les dates observées, `baseline_comparison`, la couverture de chaque dimension et `request_budget`. Les dates absentes ne sont pas remplacées par zéro. Une demande final ne prouve pas une couverture complète ; les données all peuvent évoluer et conservent `first_incomplete_date` quand Google le fournit. `_meta.sources.google.site` conserve la propriété demandée ; `_meta.params` conserve dates, filtres et options.

Une vue page peut revenir en byPage avec des totaux en byProperty. Ses deltas de lignes communes peuvent rester comparables, mais une agrégation différente ou inconnue rend la réconciliation indisponible. `observed_sums`, `matched_delta` et les résidus signés décrivent uniquement les lignes récupérées ; la surcouverture est signalée. Les vues page, query, country et device recouvrent le même trafic et ne s’additionnent pas. Une contribution ou un résidu ne prouve pas la cause d’une variation.

## Preuves du rapport et budget de sortie (depuis 1.4.0)

Le checkout source ajoute `report_contract` à `search_change_breakdown`. Il distingue les pointeurs vers les métriques observées (`facts`), les deltas et CTR calculés (`calculations`) et les preuves absentes (`unavailable`). `hypotheses` reste vide. Chaque identifiant de constat dépend de la propriété GSC exacte, de la dimension, de la clé et de la version de règle. Sur la branche source après 1.4.0, la version v2 inclut aussi moteur, type de recherche, état des données, filtres AND et base d’agrégation ; l’ordre des filtres ne change pas l’identité. Les constats sont explicitement des observations, sans hypothèse ni correctif confirmé, avec critères manquants et prochaine vérification. Un changement de version de règle change volontairement leurs identifiants. L’empreinte du snapshot couvre le rapport et toutes les observations récupérées et assainies, y compris les lignes masquées par la limite d’affichage. Elle ne stocke aucun snapshot et ne fournit aucun accès au détail.

`output_max_bytes=None` conserve le rapport complet. Un entier positif, par exemple `output_max_bytes=50000` ou `--output-max-bytes 50000` en CLI, borne l’enveloppe JSON UTF-8, métadonnées `_meta` comprises. Avec ce budget, la CLI conserve cette enveloppe même sans `--meta`. Le saut de ligne final et l’enveloppe de transport MCP sont hors du compte. Vérifiez `response_budget.status` et `serialized_bytes`.

Si les lignes dépassent le budget, la réponse contient `RESPONSE_BUDGET_EXCEEDED`. Elle retire les lignes et constats affichés avec leurs comptes et raisons d’indisponibilité, tout en conservant erreurs source, couverture et résumés. Si cette enveloppe minimale dépasse encore le plafond, l’appel lève `ResponseBudgetExceeded` avec le nombre minimal d’octets et les erreurs source. Le JSON n’est jamais coupé. Aucun accès au détail, nouvel appel automatique ou stockage durable n’est fourni.

## Comparer des périodes disjointes avec les mêmes jours de semaine (depuis 1.4.0)

```python
search_weekday_reference(
    site="sc-domain:example.com", days=28, end_date="2026-09-30",
    dimensions=["query"], filters=None, search_type="web",
    aggregation_type="auto", row_limit=1000, max_requests=20, limit=50,
)
```

Cet outil source appelle une fois `search_change_breakdown` avec `data_state="final"`. La fin par défaut est trois jours avant la date courante dans `America/Los_Angeles`. Une fin explicite doit respecter ce délai. La référence est décalée de `7 * ceil(days / 7)` jours : les périodes ont la même durée, restent disjointes et commencent le même jour de semaine, même pour une durée non multiple de sept. Le budget de requêtes physiques de l’outil enfant s’applique.

`weekday_reference` conserve dates effectives, décalage, délai, métadonnées de l’appel enfant et raisons de couverture. Des dates absentes ou des agrégats incompatibles/inconnus laissent le delta nul et le statut `unavailable`. Une demande final avec trois jours de délai ne certifie pas la complétude fournisseur. La référence observée décrit clics et impressions, sans prouver une saisonnalité annuelle, un incident du moteur ni une cause. Cet outil n’a pas de paramètre de budget de sortie en octets.

## Références annuelles, robustes et combinées (source après 1.4.0)

`search_weekday_reference` conserve son nom et son comportement par défaut (`reference_strategy="weekday"`). Les options explicites `year_on_year`, `rolling_daily` et `all` ajoutent d’autres références. Exemple : `site="sc-domain:example.com", days=28, dimensions=["query", "page", "country", "device"], reference_strategy="all", max_requests=40, history_days=56, min_support=6`.

La référence annuelle conserve la durée et la date de fin de l’année précédente ; le 29 février devient le 28 février. Le décalage des jours de semaine est signalé. Les périodes qui se recouvrent sont refusées et l’historique absent reste indisponible.

La référence robuste ajoute une requête quotidienne sur 42 à 364 jours antérieurs. Pour chaque jour de semaine de la période actuelle, elle multiplie son nombre d’occurrences par la médiane des comptes historiques observés, puis additionne ces valeurs. Six observations valides par jour de semaine et métrique sont exigées par défaut. Support, médianes, écarts absolus médians, dates absentes et fenêtre historique restent visibles. Aucun jour absent ne devient zéro ; le résultat n’est ni un test de significativité ni un effet causal.

`all` partage un seul budget de tentatives physiques entre trois rapports et la requête historique supplémentaire, sans nouvelle tentative automatique. Quatre dimensions demandent au moins 37 tentatives ; 40 est un exemple borné. Des signes contradictoires donnent `mixed`, une référence indisponible donne `undetermined`. Chaque rapport enfant conserve ses sources et dates ; son empreinte couvre le breakdown enfant, pas la requête historique ajoutée ni le contexte déclaré. Aucun budget de sortie en octets n’est ajouté à ce wrapper.

`context_json` est un registre déclaré : `version: 1`, propriété `site` exacte, `retrieved_at` ISO avec fuseau, listes `collection_incidents` et/ou `business_events`. Chaque incident porte `id`, `provider`, `report_type`, `start`, `end`, `source_url`, `uncertainty` ; un événement métier porte `id`, `kind`, `start`, `end`, `uncertainty`. Dates YYYY-MM-DD, URL HTTP sans identifiants ni query, plafond de 32768 octets et 50 éléments par famille. Une collecte vieille de plus de sept jours est périmée. Autorité et pertinence restent non vérifiées ; un chevauchement de dates ne confirme aucune cause et la santé de collecte reste inconnue. Aucun registre externe n’est interrogé.

Un `traffic_health_check` séparé peut comparer clics GSC et sessions GA4 avec ses propres sources, unités, dates, fuseaux et contrôles de compatibilité. Un ratio ne confirme pas un problème de tracking. La qualité diagnostique reste à évaluer humainement sous #6.

## Prévisualiser un export SiteOne en mémoire (depuis 1.4.0)

Le correctif source après 1.4.0 accepte les longues chaînes des annexes exclues de la sortie, sans relever le plafond de 4096 caractères des champs utilisés ni les limites globales d’octets, profondeur, UTF-8 et nombres finis. Une fixture reprend les 73 lignes de l’export public SiteOne à la révision `f3d967b190a77ff5f816b7ddab74c1a778d9dbaf` ; aucun crawler n’est exécuté et l’état actuel du site n’est pas vérifié.

```python
crawl_import_preview(report_json='{"results":[]}', producer="siteone")
```

Fournissez l’export comme chaîne JSON. Cet adaptateur source ne lit aucun chemin, ne lance aucun crawler, ne récupère aucune URL, n’installe rien, ne persiste aucune preuve et ne joint aucune donnée GSC. Il prend en charge le schéma JSON d’une révision SiteOne fixée ; les tests utilisent des fixtures de ce schéma, sans export de crawl réel. Les entrées sont bornées à 2 MiB UTF-8, 5 000 lignes et une profondeur de 20 ; l’aperçu conserve au plus 50 lignes acceptées et des échantillons bornés d’erreurs/rejets.

Le résultat conserve déclarations du producteur, URL brutes et empreintes des octets source/configuration. Sélection et fuseau d’exécution restent inconnus sans vérification. Les rejets et omissions conservent comptes et raisons. Les chaînes importées sont des données, jamais des instructions. Les valeurs supplémentaires et configurations non prises en charge sont masquées ; l’entrée brute n’apparaît jamais dans `_meta.params`. Les URL contenant des identifiants sont rejetées sans les réafficher. Les scores restent des heuristiques tierces avec `ranking_signal=false`. Un export vide ne prouve ni absence, ni bonne santé, ni non-indexation d’une page.

## Observer les destinations d’une page

`link_targets_audit(url, max_targets=30, max_requests=60)` lit une page HTTP(S) publique sans identifiants Google. Il observe ses destinations internes distinctes et conserve toutes les ancres, sans crawl récursif.

```bash
gsc-cli link-targets-audit --url https://example.com/guide/ \
  --max-targets 30 --max-requests 60 --meta
```

Une ancre synthétique vers une destination répondant 404 peut produire :

```json
{
  "targets": [{
    "requested_url": "https://example.com/missing/",
    "final_url": "https://example.com/missing/",
    "status_code": 404,
    "outcome": "observed",
    "availability_reason": null,
    "source_links": [{"href": "/missing/", "absolute_url": "https://example.com/missing/", "anchor": "Previous guide", "zone": "body", "rel": ""}],
    "findings": ["http_not_found"]
  }]
}
```

Un timeout, un refus de sécurité ou une requête ignorée laisse le statut terminal et l’URL finale à null avec une raison d’indisponibilité. Les sauts déjà reçus et `last_observed_status` peuvent survivre à un échec ultérieur sans devenir le statut terminal. Les URL demandées/finales, horodatages et associations d’ancres restent dans le résultat. Hrefs, ancres et destinations de redirection sont du contenu non fiable.

`max_targets` accepte 1..100 et `max_requests` 1..200. Les GET source, sauts de redirection et tentatives HTTP échouées partagent le budget. Une chaîne suit au maximum cinq redirections. `coverage` vaut complete, partial ou unavailable ; complete signifie que toutes les destinations éligibles découvertes ont terminé, même avec un 404 observé. Les comptes décrivent le HTML analysé, pas tout le site. Les lignes ignorées conservent la raison budget ou deadline ; hrefs vides, fragments seuls, liens externes, non-HTTP et malformés ont des comptes d’exclusion.

Les identités de requête retirent fragments et ports par défaut, normalisent scheme et hostname, mais conservent ordre et répétitions de query, casse du chemin, échappements et slash final. Les requêtes sont dédupliquées sans perdre les occurrences d’ancres. L’éligibilité permet un alias www initial et les ports HTTP:80/HTTPS:443 ; les identités avec/sans www restent séparées. Un port non standard doit correspondre numériquement. Les liens relatifs utilisent l’URL source servie ; HTML base est ignoré.

L’analyse exige un corps source terminal 2xx complet. Les octets bruts conservés en encodage identity sont bornés à 1 MiB ; les encodages de contenu non pris en charge sont refusés. Le décodage UTF-8 remplace les octets invalides. Les corps de redirection et de destination ne sont pas lus. Le plafond borne la rétention/consommation applicative, pas le trafic socket exact. La deadline de 60 secondes borne la planification coopérative sans pouvoir annuler DNS ou socket synchrones ; `budgets.deadline_overrun` signale le dépassement. Le transport utilise le pinning IPv4/A ; les hôtes uniquement IPv6 et la contention du verrou sont indisponibles.

Un statut HTTP défaillant permet de vérifier le lien concerné. Il ne prouve ni indexation Google, ni impact de classement, ni gain de trafic garanti. Continuez avec l’[audit complet](/fr/docs/examples/full-audit/), l’[investigation de trafic](/fr/docs/examples/traffic-drop/) et les [limites de preuve](/fr/docs/evidence-and-safety/).

## Suivre un changement déclaré (depuis 1.4.0)

`seo_change_impact` est inclus dans la version 1.4.0 et son registre de 89 outils. L’exemple ci-dessous est explicatif : l’événement est déclaré par l’appelant, sans preuve de déploiement ni suivi réel.

```python
seo_change_impact(
    event={"site": "sc-domain:example.com", "url": "https://example.com/guide/",
           "changed_at": "2026-09-15T12:00:00+02:00", "timezone": "Europe/Paris",
           "description": "Revised page title", "revision": "caller-revision"},
    baseline_start="2026-09-08", baseline_end="2026-09-14",
    comparison_start="2026-09-16", comparison_end="2026-09-22",
    filters=None, search_type="web", align_weekdays=False,
    page_mapping=None, concurrent_changes=["Caller reports a concurrent navigation edit"],
    row_limit=1000, max_requests=20, limit=50,
)
```

L’événement exige `site`, `url`, `changed_at`, `timezone` et `description`. `revision` et `baseline_id` restent des déclarations facultatives. L’horodatage comprend les secondes et un décalage explicite conforme au fuseau IANA. La dépendance `tzdata` fournit une base de secours lorsque le système n’en possède pas. Aucun instant de déploiement n’est déduit de Git ou du HTML. L’appelant conserve l’événement et le rapport ; `persistence.status` vaut `not_persisted`.

Les fenêtres inclusives ont la même durée, sont ordonnées et ne se chevauchent pas. Elles excluent toute la date de l’événement dans le calendrier Google `America/Los_Angeles`. `align_weekdays=True` impose aussi le même jour de semaine au début des fenêtres. Le délai de trois jours de `maturity_policy` est une politique préalable ; `provider_finalization_verified=false` ne certifie pas la finalisation des observations.

L’outil réutilise `search_change_breakdown` avec des filtres identiques et des demandes de données finales. Les filtres de page fournis par l’appelant sont refusés. `page_mapping`, facultatif, contient exactement `baseline_url` et `comparison_url`, dont l’une correspond à l’URL effective de l’événement. Deux URL distinctes sont interrogées ensemble dans chaque fenêtre : les totaux concernent ce périmètre combiné, sans découverte de canonique ni de redirection. Consultez la couverture, les dates et lignes manquantes, les budgets et la compatibilité d’agrégation dans `search_evidence`.

`comparison.status` vaut `observed` ou `unavailable`. Un suivi absent ou trop récent conserve `insufficient_post_change_data`. Une référence absente, une agrégation incompatible ou une erreur fournisseur conservent leurs motifs. Les valeurs nulles ne deviennent pas des zéros. Des comptages bruts peuvent rester disponibles même si la comparaison ne l’est pas ; `descriptive_delta` reste alors nul. Les deltas observés portent sur les clics, impressions et points de pourcentage de CTR. L’intervalle de collecte est horodaté en UTC.

`concurrent_changes` conserve les déclarations de l’appelant. Saisonnalité, changements des moteurs et autres modifications peuvent affecter les fenêtres. `attribution.causal_effect` reste nul avec `status=not_identified` : aucun gain causal, ROI, significativité ou classement garanti n’est établi. Les fixtures ne prouvent pas l’utilité pour une propriété réelle. Consultez les [workflows éditoriaux](/fr/docs/editorial-workflows/) pour les contrôles avant publication.

## Logs serveur locaux (source après 1.4.0)

`crawl_log_audit(log_path, site)` lit progressivement un fichier Apache common/combined sélectionné par l’appelant. La sortie masque par défaut chemins lisibles, queries, IP clients, utilisateurs, referrers et lignes brutes. Vérifiez couverture, hash des octets consommés, fenêtre UTC et limites atteintes. Les étiquettes de robots sont déclarées ; une appartenance aux plages Google actuelles ne prouve ni identité historique ni indexation. Aucune jointure n’est effectuée. Consultez le [contrat local et exemple CLI](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/crawl-log-audit.md).


## Snapshots locaux de crawl

Commencez par `crawl_snapshot_import` en mode aperçu avant de choisir `persist=True`. Gardez la propriété exacte et le snapshot ID. `crawl_snapshot_read` pagine les lignes compatibles ; `crawl_snapshot_join` accepte des rapports GSC par page et link map fournis, sous limites. Les URL brutes et inconnues restent explicites. La rétention est locale et la purge explicite ; aucun crawl ni upload n’est lancé. Consultez le [contrat d’inventaire versionné et de purge](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/crawl-snapshots.md).

`crawl_diff` compare deux inventaires stockés sans crawl. Conservez les deux sources, les raisons de compatibilité et les changements omis ; une URL absente ne prouve pas sa suppression. Les politiques par champ restent limitées aux lignes communes retenues.

`indexing_evidence_matrix` rapproche un échantillon explicite d’URLs avec des observations fournies d’inspection, HTML, GSC, inventaire et logs, et un snapshot optionnel. Origine/dates restent déclarées, contradictions visibles et indexation actuelle inconnue. Consultez le [contrat de la matrice](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/indexing-evidence-matrix.md).
