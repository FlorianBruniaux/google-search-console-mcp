---
title: "Audits à périmètre borné"
description: "Comparer des fenêtres Google explicites et observer les destinations des liens internes avec leurs limites de couverture."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/audit-workflows/
---

`search_change_breakdown` et `link_targets_audit` sont inclus dans `gsc-mcp-tools==1.3.0`, qui expose 85 outils. Suivez les [instructions d’installation](/fr/docs/installation/). Les exemples ci-dessous sont des fragments synthétiques explicatifs, sans appel réel à Google ou au réseau.

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
