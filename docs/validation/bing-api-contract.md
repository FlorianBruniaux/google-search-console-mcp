# Contrat Bing Webmaster API

## Verdict

`UNKNOWN`. Aucun canari réel n'a été exécuté. `Step 4` et `Gate G2` ne sont pas satisfaits. Task 3 doit rester bloquée.

## Portée de cette validation

- Date du rapport: `2026-09-05`.
- Date du canari: `UNKNOWN`, canari non exécuté.
- Version du package inspectée localement: `1.1.2`.
- Version réellement exercée contre Bing: `UNKNOWN`.
- Cause: `BING_WEBMASTER_API_KEY`, `BING_TEST_SITE`, `BING_TEST_PAGE`, `BING_TEST_FEED` et `BING_TEST_QUERY` ne sont pas disponibles dans l'environnement de validation.
- Réseau: aucun appel effectué.
- Preuve disponible: tests offline du validateur de forme et de ses garde-fous de redaction. Ces tests ne prouvent ni le contrat Bing réel, ni les codes HTTP, ni la fraîcheur des données.

Le validateur appelle uniquement les 17 méthodes présentes dans `READ_METHODS`. Il ne produit que les noms de champs, les types, les comptes, les bornes de dates dérivées et les métadonnées d'erreur déjà expurgées. Il ne produit aucun paramètre d'appel, payload brut, clé API, URL, requête, `AuthenticationCode` ou `DnsVerificationCode`.

## Matrice d'observation

| Méthode | Exécution réelle | HTTP observé | Clés observées | Fenêtre min/max | Verdict |
| --- | --- | --- | --- | --- | --- |
| `GetUserSites` | Non | `UNKNOWN` | `UNKNOWN` | Sans objet | `UNKNOWN` |
| `GetQueryStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetPageStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetPageQueryStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetRankAndTrafficStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetCrawlStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetCrawlIssues` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetCrawlSettings` | Non | `UNKNOWN` | `UNKNOWN` | Sans objet | `UNKNOWN` |
| `GetUrlInfo` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetUrlTrafficInfo` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetFeeds` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetFeedDetails` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetKeywordStats` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetRelatedKeywords` | Non | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `GetLinkCounts` | Non | `UNKNOWN` | `UNKNOWN` | Sans objet | `UNKNOWN` |
| `GetUrlLinks` | Non | `UNKNOWN` | `UNKNOWN` | Sans objet | `UNKNOWN` |
| `GetUrlSubmissionQuota` | Non | `UNKNOWN` | `UNKNOWN` | Sans objet | `UNKNOWN` |

## Questions contractuelles non résolues

- Fréquence constatée de mise à jour: `UNKNOWN`.
- Sémantique observée de `DailyQuota`: `UNKNOWN`, limite totale ou capacité restante non déterminée.
- Sémantique observée de `MonthlyQuota`: `UNKNOWN`, limite totale ou capacité restante non déterminée.
- Champs absents par rapport à la documentation Microsoft: `UNKNOWN`.
- Existence d'au moins une propriété avec `IsVerified=true`: `UNKNOWN`.
- Locale de requête utilisée par le harnais pour les méthodes keyword: `US` et `en`, paramètre de canari non validé contre Bing et non présenté comme valeur par défaut du futur outil public.

## Gate G2

Les quatre méthodes critiques restent `UNKNOWN`:

- `GetQueryStats`
- `GetPageStats`
- `GetCrawlStats`
- `GetUrlSubmissionQuota`

Conclusion: `Gate G2 = NOT SATISFIED`. Ne pas figer les parseurs de Task 3 sur les seuls exemples Microsoft. Il faut exécuter le canari hors CI avec une propriété de test réelle, puis remplacer uniquement les cellules prouvées par `VERIFIED` ou `PARTIAL` avec le code HTTP, les clés et les fenêtres effectivement observés.
