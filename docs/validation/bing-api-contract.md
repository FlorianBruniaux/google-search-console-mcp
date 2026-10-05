# Contrat Bing Webmaster API

## Verdict

`PARTIAL`. Le canari réel expurgé du `2026-10-05` a réussi 15 lectures sur 17 avec la version `1.1.2` du package. `GetKeywordStats` et `GetRelatedKeywords` ont répondu HTTP 400 et restent `UNKNOWN`.

`Gate G2 = SATISFIED` pour `GetQueryStats`, `GetPageStats`, `GetCrawlStats` et `GetUrlSubmissionQuota`. Task 3 est débloquée. Ce gate ne transforme pas le verdict global en `VERIFIED` et ne valide pas les deux méthodes keyword.

## Portée de cette validation

- Le canari appelle uniquement les 17 méthodes présentes dans `READ_METHODS`.
- Les 15 lectures réussies ont retourné HTTP 200. Les deux lectures keyword ont retourné HTTP 400.
- La sortie conservée contient uniquement les noms de champs autorisés, les types, les comptes et les bornes de dates dérivées.
- Aucun paramètre d'appel, payload brut, secret, domaine, URL, requête, `AuthenticationCode` ou `DnsVerificationCode` n'est reporté ici.
- Les clés non résumées dans la preuve expurgée restent indiquées comme non conservées. Elles ne sont pas reconstruites depuis les exemples Microsoft.

Le validateur conserve le statut HTTP réellement retourné par le transport. Il remplace tout nom de champ inconnu par `<redacted-key>`. Un code d'erreur Bing brut n'est jamais sérialisé: `Timeout`, `TransportError` et `InvalidJson`, générés localement, ont une catégorie fixe; tout autre code devient `api_error`.

## Matrice d'observation

| Méthode | HTTP observé | Forme ou clés observées | Fenêtre observée | Verdict |
| --- | --- | --- | --- | --- |
| `GetUserSites` | 200 | Liste plate non vide; `IsVerified` observé; autres clés non conservées dans le résumé | Sans objet | `VERIFIED` |
| `GetQueryStats` | 200 | Liste plate non vide; clés exactes non conservées dans le résumé | `2026-09-11` à `2026-10-02` | `VERIFIED` |
| `GetPageStats` | 200 | Liste plate non vide avec la clé `Query`; la forme seule ne prouve pas que ses valeurs sont des URL | `2026-09-11` à `2026-10-02` | `VERIFIED` |
| `GetPageQueryStats` | 200 | Liste plate non vide; clés exactes non conservées dans le résumé | `2026-09-18` à `2026-09-25` | `VERIFIED` |
| `GetRankAndTrafficStats` | 200 | Liste avec seulement `Date`, `Clicks`, `Impressions`; aucune position observée | `2026-09-07` à `2026-10-03` | `VERIFIED` |
| `GetCrawlStats` | 200 | Liste plate non vide; clés exactes non conservées dans le résumé | `2026-09-08` à `2026-10-01` | `VERIFIED` |
| `GetCrawlIssues` | 200 | Liste vide; forme d'un élément non observée | Sans donnée datée | `PARTIAL` |
| `GetCrawlSettings` | 200 | Dictionnaire avec `CrawlRate` et une clé expurgée | Sans objet | `PARTIAL` |
| `GetUrlInfo` | 200 | `AnchorCount`, `DiscoveryDate`, `DocumentSize`, `HttpStatus`, `IsPage`, `LastCrawledDate`, `TotalChildUrlCount`, `Url`; `InIndex` absent de cette réponse | Dates d'objet observées, pas de série | `VERIFIED` |
| `GetUrlTrafficInfo` | 200 | `Clicks`, `Impressions`, `IsPage`, `Url` | Sans série datée | `VERIFIED` |
| `GetFeeds` | 200 | Liste plate non vide; clés exactes non conservées dans le résumé | `UNKNOWN` | `VERIFIED` |
| `GetFeedDetails` | 200 | Liste non vide, et non objet unique; clés exactes non conservées dans le résumé | `UNKNOWN` | `VERIFIED` |
| `GetKeywordStats` | 400 | Aucun payload exploitable | `UNKNOWN` | `UNKNOWN` |
| `GetRelatedKeywords` | 400 | Aucun payload exploitable | `UNKNOWN` | `UNKNOWN` |
| `GetLinkCounts` | 200 | Dictionnaire imbriqué avec `Links`, `TotalPages`; schéma des éléments non détaillé | Sans objet | `PARTIAL` |
| `GetUrlLinks` | 200 après utilisation du paramètre `link` | Dictionnaire imbriqué avec `Details`, `TotalPages`; schéma des éléments non détaillé | Sans objet | `PARTIAL` |
| `GetUrlSubmissionQuota` | 200 | Dictionnaire avec `DailyQuota`, `MonthlyQuota`; types observés, sémantique non déterminée | Sans objet | `PARTIAL` |

## Limites contractuelles

- Fréquence constatée de mise à jour: `UNKNOWN`.
- Sémantique de `DailyQuota` et `MonthlyQuota`: `UNKNOWN`, limite totale ou capacité restante non déterminée.
- Forme non vide de `GetCrawlIssues`: `UNKNOWN`.
- Schéma détaillé des éléments imbriqués de `GetLinkCounts` et `GetUrlLinks`: `UNKNOWN`.
- Contrat exploitable de `GetKeywordStats` et `GetRelatedKeywords`: `UNKNOWN` après HTTP 400.
- `GetPageStats.Query` est un nom de champ observé. La forme expurgée ne permet pas d'affirmer la nature de ses valeurs.
- HTTP 200 prouve seulement l'acceptation et la forme de la réponse du canari. Il ne prouve ni indexation, ni récrawl, ni effet SEO.

## Conséquences d'implémentation

- Les parseurs des quatre méthodes de `Gate G2` peuvent être construits depuis cette preuve observée, avec conservation explicite des limites ci-dessus.
- `GetUrlLinks` doit transmettre `link`, jamais `url`.
- `GetKeywordStats` et `GetRelatedKeywords` ne doivent pas être enregistrés comme outils fonctionnels dans cette version.
- La liste retournée par `GetFeedDetails` ne doit pas être figée comme un objet unique.
