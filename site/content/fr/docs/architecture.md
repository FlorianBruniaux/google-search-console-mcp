---
title: "Architecture"
description: "Comprendre le serveur MCP, les limites entre fournisseurs et les écritures protégées."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/architecture/
---

## Vue d’ensemble

Search Console MCP expose une interface MCP sur `stdio`. Le serveur et la CLI partagent le même registre d’outils. Chaque famille de fournisseur conserve son authentification, ses erreurs et ses sémantiques.

## Sélection au démarrage (depuis 1.3.1)

Depuis la version 1.3.1, `tool_selection.py` valide `GSC_MCP_TOOL_FAMILIES` avant d’enregistrer les outils MCP. Sans variable, ou avec `all`, le serveur expose tout le catalogue : 85 outils dans la version publiée 1.3.1, 87 dans le checkout source. Une liste sélectionne les familles demandées et conserve `core`. Une sélection vide ou inconnue empêche le démarrage. La CLI conserve le catalogue complet. Redémarrez le processus après une modification ; cette sélection ne change ni les identifiants ni les permissions ou confirmations nécessaires. Consultez la [configuration des familles](/fr/docs/installation/).

## Sources de données

- Google Search Console : propriétés, performances, inspection d’URL et sitemaps.
- Bing Webmaster Tools : sites, performances, crawl, feeds et backlinks selon l’API disponible.
- GA4, CrUX et PageSpeed : fournisseurs optionnels avec leurs propres autorisations.
- Pages publiques : HTML, robots.txt, sitemaps, métadonnées, schémas et liens internes.
- IndexNow : canal de notification séparé, avec une clé vérifiable par hôte.

## Frontières

Une propriété est toujours un paramètre explicite. Les résultats Google et Bing ne sont pas fusionnés. Les lectures de pages arbitraires passent par les protections réseau du serveur. Les sorties structurées conservent les métadonnées nécessaires à l’interprétation.

## Ajouts de la version 1.3.0

Le registre de la version 1.3.0 compte 85 outils. `ga4_ai_referrals` mesure les visites attribuées à des sources d’assistants documentées, après contrôle de compatibilité et avec des parts conditionnées par la couverture. Les sources candidates restent séparées.

`traffic_health_check` aligne les dates demandées et préserve les états zéro, vide, inconnu et indisponible. Les rapports combinés par page gardent encore leurs fenêtres indépendantes. Les métadonnées décrivent la méthode de chaque verdict ou score concerné sans modifier sa valeur. Cinq audits marquent leur HTML principal non fiable ; le détecteur de challenge protège la validation de schémas et l’audit éditorial.

Consultez les [limites de preuve](/fr/docs/evidence-and-safety/) avant d’interpréter un ratio, un score, un signal d’instruction ou une visite attribuée.

## Correctifs de la version 1.3.1

`traffic_drops` compare deux fenêtres adjacentes de même durée, avec une fin de fenêtre courante trois jours avant aujourd’hui. `seo_lost_queries` conserve sa fenêtre terminant aujourd’hui. Les `diagnosis_candidates`, leur `diagnosis_status` et les métriques précédentes/courantes documentent des règles, sans prouver de cause. Les candidats de classement et CTR exigent des impressions dans les deux périodes ; la baisse de demande exige une diminution observée des impressions. Une requête absente des lignes courantes figure dans `unavailable_queries` avec `metrics_current=null`. Son absence ne prouve pas un trafic nul ; CTR et position restent `null` avec zéro impression.

`seo_cannibalization` conserve son score HHI mais exclut par défaut les requêtes contenant `site:`, `intitle:`, `inurl:` ou `filetype:`. `excluded_search_operator_queries` compte les chaînes distinctes exclues. `include_search_operators=True` les réintègre et conserve ce choix dans les métadonnées. Ces opérateurs peuvent volontairement renvoyer plusieurs pages.

`bing_query_stats` agrège par requête avant le tri et la limite ; `daily=True` restitue les lignes quotidiennes. Les CTR source contradictoires restent indisponibles avec leurs diagnostics, même si la somme masque la contradiction. Le CTR utilise les totaux et les positions disponibles leurs pondérations respectives. Les adaptateurs Bing conservent aussi ces anomalies dans les comparaisons. Voir les [exemples Bing](/fr/docs/bing-setup/).

`ai_visibility_audit` distingue `ClaudeBot` pour l’entraînement, `Claude-User` pour la navigation demandée par l’utilisateur et `Claude-SearchBot` pour la recherche, selon la [documentation des robots Anthropic](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler). Une permission robots.txt ne prouve pas une activité de crawl ou une citation IA.

## Outils d’écriture

Une écriture suit cette séquence : lecture de l’état, calcul du périmètre, confirmation explicite, appel du fournisseur, puis vérification de la réponse. L’acceptation d’une demande reste distincte de l’état futur de crawl ou d’indexation.

## Exécution

Le client lance normalement un processus serveur enfant par session active. Évitez de lancer un démon manuel en parallèle. Consultez le [guide d’installation](/fr/docs/installation/) pour mesurer les processus actifs.

[Lire la version anglaise canonique](/docs/architecture/).

## Profil éditorial

`editorial_audit` applique un profil FR/EN versionné aux passages HTML éligibles. Les alertes renvoient leurs extraits, emplacements et limites ; elles ne mesurent ni une probabilité d’écriture IA ni une pénalité de classement. Les instructions demandent de conserver le sens des propositions sans le certifier ; l’outil reste distinct de `content_quality` et n’appelle aucun classificateur. Voir le [profil éditorial](/fr/docs/editorial-audit/).

`search_change_breakdown` compare des fenêtres Google explicites de même durée ; `link_targets_audit` observe les destinations internes publiques dans un budget partagé avec la source. Les [audits à périmètre borné](/fr/docs/audit-workflows/) détaillent leurs paramètres, résultats et limites.

## Suivi et brouillons source non publiés

Le registre source contient 87 outils : `seo_change_impact` et `rewrite_fidelity_check` s’ajoutent aux 85 outils de la version publiée 1.3.1. `change_impact.py` conserve les événements déclarés et réutilise la couverture de `search_change_breakdown`, sans persistance ni attribution causale. Les fuseaux IANA utilisent la base système ou le secours `tzdata` fourni. `editorial_drafts.py` adapte le texte/Markdown borné au cœur de règles existant, sans récupération réseau, exécution ni lecture de fichier. `rewrite.py` compare littéraux protégés et qualificatifs avec des ancres lexicales locales ; les dimensions sémantiques restent non évaluées. Consultez les [audits bornés](/fr/docs/audit-workflows/) et [workflows éditoriaux](/fr/docs/editorial-workflows/).
