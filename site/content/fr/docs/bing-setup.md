---
title: "Configurer Bing Webmaster Tools"
description: "Configurer la clé de compte Bing, vérifier les sites accessibles et distinguer IndexNow."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/bing-setup/
---

## Deux clés différentes

`BING_WEBMASTER_API_KEY` authentifie le compte Bing Webmaster Tools. Une même clé peut exposer plusieurs sites vérifiés visibles par ce compte. Chaque appel indique encore explicitement le `site` cible.

La clé IndexNow est différente. Elle est liée à un hôte et doit être publiquement vérifiable sur cet hôte. Ne réutilisez pas la clé de compte Bing comme clé IndexNow.

## Ajouter la clé de compte

Créez une clé dans Bing Webmaster Tools, conservez-la dans un gestionnaire de secrets, puis injectez-la dans l’environnement du serveur MCP sous le nom `BING_WEBMASTER_API_KEY`.

Ne commitez jamais cette valeur et ne la collez pas dans une conversation publique.

## Vérifier les sites accessibles

Utilisez d’abord l’outil de liste des sites Bing. Vérifiez que les URL retournées correspondent exactement aux variantes attendues, notamment le protocole et le sous-domaine. Une clé valide ne garantit pas l’accès à un site non vérifié dans le compte.

## Agrégation des requêtes (depuis 1.3.1)

Depuis la version 1.3.1, `bing_query_stats` renvoie une ligne par requête par défaut. Il agrège les dates source dans la fenêtre locale demandée avant le tri et la limite. Les clics et impressions sont additionnés ; le CTR est leur ratio. Les positions disponibles sont pondérées par leurs nombres de clics ou d’impressions respectifs.

```bash
# Totaux par requête, comportement par défaut depuis 1.3.1
gsc-cli bing-query-stats --site https://example.com/ --days 28 --limit 20
# Lignes source quotidiennes
gsc-cli bing-query-stats --site https://example.com/ --days 28 --limit 20 --daily
```

Un CTR source contradictoire, par exemple davantage de clics que d’impressions, reste `null` avec ses diagnostics. L’agrégation et la limite ne masquent pas cette anomalie ; le CTR n’est pas plafonné à 100 %. Contrôlez la fenêtre observée et la couverture. L’agrégation ne rend pas la fenêtre Bing exacte et ne prouve pas la fraîcheur des données. La version publiée 1.3.0 conserve son comportement quotidien antérieur.

Les positions absentes ou nulles à la source sont renvoyées à `null`. Les comptes manquants conservent leurs valeurs numériques historiques, avec le marqueur `unavailable_metrics` et une preuve d’indisponibilité pour chaque champ concerné. Le CTR et les agrégats pondérés signalent aussi leurs données d’entrée indisponibles. Un zéro explicitement fourni par Bing reste une observation.

## Écriture et IndexNow

Les soumissions sont bornées par une cible et une action explicites. Avant un envoi, confirmez le fournisseur, le site, les URL et la clé utilisée. Une réponse acceptée prouve la réception de la demande, pas un crawl ou une indexation.

## Diagnostic

- `401` ou `403` : contrôler la clé, le compte et les permissions du site.
- Site absent : vérifier la propriété dans Bing Webmaster Tools.
- IndexNow refusé : vérifier la clé sur l’hôte cible et l’URL du fichier de validation.
- Données vides : contrôler la fenêtre observée et la disponibilité du rapport avant de conclure à une absence de visibilité.

[Lire la version anglaise canonique](/docs/bing-setup/).
