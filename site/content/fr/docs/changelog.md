---
title: "Historique des versions"
description: "Résumé français des versions de Search Console MCP et lien vers l’historique canonique."
lang: fr
lastUpdated: 2026-10-09
canonicalEnglish: /docs/changelog/
---

Cette page résume les changements utiles aux utilisateurs. L’[historique anglais](/docs/changelog/) reste la source exhaustive.

## Version 1.5.0, 9 octobre 2026

Le registre contient 96 outils, soit sept ajouts. Les imports et rapprochements locaux conservent les sources, les données manquantes et les limites d’observation.

- Ajouter un profil Trafilatura optionnel à `content_quality`, avec provenance, version, paramètres et hash ; appels indépendants, échec d’extraction indisponible sans score de substitution (#41). Le profil visible par défaut reste inchangé.

- Ajouter `indexing_evidence_matrix` : observations fournies par URL, contradictions sourcées et chaînes canoniques littérales bornées ; aucune acquisition ni inférence d’indexation actuelle ou de rendu (#44).

- Ajouter `crawl_diff` pour deux snapshots de même propriété : différences bornées d’inventaire et de champs compatibles, indexation/suppression inconnues, refus des clés ambiguës et politique CI sur champs nommés (#48).

- Ajouter des snapshots de crawl versionnés : stockage local privé optionnel, quotas et idempotence, inventaire paginé, purge explicite et rapprochement borné avec des rapports GSC/link map fournis (#42). Les métadonnées fournies ne prouvent pas l’origine fournisseur.

- Ajouter `crawl_log_audit` et son guide partagé : lecture locale bornée, champs sensibles masqués, couverture explicite et vérification optionnelle des plages IP Google actuelles (#43). Identité historique et indexation restent non vérifiées.

- Accepter les longues chaînes des annexes SiteOne exclues de la sortie, sans modifier les limites des champs utilisés ni les limites globales. Ajouter une fixture d’export public avec licence et rejouer ses 73 lignes (#42, compatibilité).

- Étendre les références de trafic avec historique annuel, médianes quotidiennes, résultats mixtes/indéterminés et contexte métier/incidents déclaré (#46), sous un budget global de tentatives. Le comportement par défaut reste identique, sans attribution causale.

- Aligner les outils autorisés des agents avec les guides partagés ; borner les tentatives d’agents et les octets de sources transmis à la synthèse, vérifier la propriété des URLs et conserver les branches ignorées (#39, pilote). Les budgets fournisseurs et l’exécution native restent non vérifiés.

- Conserver les zéros explicites et les métriques d’apparence indisponibles, les dates demandées et la propriété source ; distinguer les réponses partielles ou malformées sans inférer une exposition IA (#37).
- Les identifiants des constats incluent les options source et la version de règle v2 ; observations, critères manquants et vérification restent explicites dans le budget d’octets du rapport complet (#40).

- Quatre parcours bilingues par profil et un catalogue des 89 outils généré depuis le registre, avec périmètres de contrôle et exemples sourcés.
- Les 13 playbooks SEO partagent leur source dans `.agents/skills/` entre Claude et Codex. Correction des appels non pris en charge et des affirmations non étayées sur les pénalités, pertes IA, résultats enrichis et gains de positions. Vérification des projections, signatures et scénarios BM25 du dépôt (#38).

## 1.4.0 (2026-10-09)

- Ajout de plans du site HTML et de pages de nouveautés datées dans les deux langues, accessibles depuis le bandeau d’accueil, la navigation et les pieds de page. Les nouveautés reprennent l’historique et distinguent le code source des versions publiées sur PyPI.
- `seo_change_impact` associe un événement déclaré à des fenêtres Google descriptives, avec couverture conservée, sans persistance ni effet causal identifié (#23).
- `editorial_audit` accepte des brouillons plain/Markdown bornés avec langue FR/EN explicite, contenu protégé et emplacements Unicode (#24).
- `rewrite_fidelity_check` signale les changements mécaniques de littéraux et qualificatifs à relire ; même sans alerte, la fidélité sémantique reste non évaluée (#20).
- `search_weekday_reference` compare des périodes Google égales, disjointes et alignées sur les jours de semaine, jusqu’à J-3 en date Pacifique, avec demande de données finales. Une couverture incomplète rend la référence indisponible ; elle ne mesure ni effet annuel ni causalité.
- `crawl_import_preview` lit en mémoire un JSON SiteOne fourni par l’appelant, sous limites fixes, sans fichier, réseau, secret ou jointure GSC. Les scores proviennent du crawler.
- `search_change_breakdown` ajoute une empreinte déterministe de provenance sans stockage, accepte une seule dimension et peut borner le JSON UTF-8 complet, métadonnées comprises. La CLI conserve le JSON retourné après dépassement ; un plafond insuffisant pour l’enveloppe minimale échoue explicitement sans JSON.
- `ai_overviews_impact` présente des apparences de recherche Web génériques, sans preuve d’exposition IA. Les rôles et playbooks Claude conservent les inconnues ; 12 tests passent dans un hôte contrôlé, sans validation de l’exécution Claude native. La CI de PR est réservée au propriétaire ; le workflow de publication relance les tests et valide le wheel avant son envoi.
- La version 1.4.0 contient 89 outils, contre 85 pour les versions 1.3.0 et 1.3.1. Les [workflows éditoriaux](/fr/docs/editorial-workflows/) et [audits bornés](/fr/docs/audit-workflows/) précisent les limites.

## 1.3.1 (2026-10-08)

- Sélection facultative des familles MCP via `GSC_MCP_TOOL_FAMILIES`, avec catalogue complet par défaut, `core` conservé et CLI complète. Aucune permission fournisseur n’est accordée par cette sélection.
- Listes de chaînes CLI transmises par options répétées ou tableaux JSON, sans découper les virgules des URL. Les tableaux invalides sont refusés avant l’appel fournisseur.
- `traffic_drops` termine la fenêtre courante trois jours avant aujourd’hui. Les diagnostics sont des candidats documentés ; les requêtes courantes absentes restent indisponibles. Le comportement de `seo_lost_queries` est conservé.
- `seo_cannibalization` exclut les requêtes avec opérateurs de recherche, expose leur nombre distinct et accepte `include_search_operators=True`.
- Robots Anthropic actuels : `ClaudeBot`, `Claude-User`, `Claude-SearchBot`, avec leurs rôles distincts.
- `bing_query_stats` agrège par requête avant tri et limite ; `daily=True` conserve les lignes quotidiennes. Un CTR source contradictoire reste `null` avec ses diagnostics, même après agrégation.
- Les rapports Bing renvoient à `null` les positions absentes ou nulles à la source. Les nombres de clics ou d’impressions manquants gardent leurs valeurs historiques avec `unavailable_metrics` et une preuve d’indisponibilité ; les vrais zéros restent des observations. Les agrégats et totaux conservent ces marqueurs. Chaque écart entre moteurs devient indisponible si une donnée nécessaire manque.
- `quick_wins` exclut les lignes dont le CTR est indisponible et indique leur nombre au lieu d’échouer sur une métrique nulle.

## 1.3.0

- Ajout de `search_change_breakdown` pour des fenêtres Google explicites, dimensions indépendantes, couverture et résidus descriptifs (#21).
- Ajout de `link_targets_audit` pour les statuts GET des destinations internes et leurs redirections, avec les ancres source (#19). Transport indisponible et erreur HTTP observée restent distincts.
- La version 1.3.0 compte 85 outils, contre 81 pour 1.2.0. Le [guide bilingue des audits bornés](/fr/docs/audit-workflows/) documente les appels et limites ; l’évaluation des classifieurs reste dans la documentation contributeur.

- Ajout de `editorial_audit`, profil éditorial FR/EN versionné avec extraits localisés et consignes de réécriture fidèle (#17). Les citations, le code et les exceptions de genre sont protégés. Aucun score d’écriture IA ou de classement.
- `content_quality` conserve son API et son score.

- Ajout de `ga4_ai_referrals` pour les visites attribuées aux sources d’assistants documentées. Cet outil rejoint le registre partagé. Les candidats restent exclus des totaux confirmés et une couverture insuffisante empêche le calcul de parts.
- Les verdicts et scores disposent de métadonnées par champ pour distinguer observations, calculs, règles et preuves indisponibles, sans probabilité inventée ni autorisation implicite d’action.
- Les audits de titres, liens internes, technique et schémas signalent certains motifs d’instructions françaises et anglaises dans le HTML. Le contenu récupéré reste non fiable même sans signalement.
- La comparaison GSC/GA4 aligne les dates demandées et distingue zéro, réponse vide et source indisponible. Les filtres ou couvertures incompatibles empêchent un ratio ; les statuts disponibles restent des heuristiques.
- La validation de schémas distingue un challenge SiteGround connu de la page demandée. Les schémas restent indisponibles pour ce verdict ; les tests sont synthétiques.

- Les rapports GA4 identifient la propriété effectivement interrogée, même avec la configuration par défaut. Les rapports combinés conservent cette provenance et le site GSC ; une source GA4 inconnue reste `null`.
- La validation des schémas parcourt les nœuds JSON-LD `@graph`, y compris dans un tableau racine, et conserve les parents typés. Un `@type` en liste est pris en charge sans erreur.
- Les champs recommandés de `SoftwareApplication` restent distincts des champs requis. La validation locale des champs ne prétend pas établir l’éligibilité Google aux résultats enrichis.
- Les audits de schémas et de liens suivent au plus cinq redirections vers le même site, avec validation de sécurité à chaque saut. Les redirections vers un autre site ou une URL malformée renvoient une erreur de récupération.
- Les audits de schémas et de liens internes indiquent l’URL finale. Les outils de liens utilisent cette URL pour distinguer les liens internes après une redirection vers `www`.
- L’audit des titres ne signale plus `TL;DR` comme un titre vide.

- La landing et les scénarios utilisent des titres factuels avec des chiffres explicites.
- La FAQ pose des questions directes en anglais et en français.
- Les pages documentaires ajoutent `hreflang="x-default"` et le site publie un `llms.txt` limité aux ressources destinées aux utilisateurs.

## 1.2.0

- Intégration de Bing Webmaster Tools avec séparation claire entre la clé de compte et IndexNow.
- Outils et documentation étendus pour les workflows multi-fournisseurs.
- Configuration de publication PyPI par identité fédérée.
- Réduction du risque de processus MCP dupliqués dans les exemples d’installation.

## 1.1.x

- Audits des titres, liens internes et équité de liens.
- Corrections de compatibilité du runtime MCP et des redirections sûres.

## Versions antérieures

Les versions précédentes ont construit les briques Search Console, inspection d’URL, sitemaps, GA4, CrUX, PageSpeed, schémas, audits publics et sorties JSON structurées.

Pour les détails exacts, migrations et correctifs, consultez la [version anglaise canonique](/docs/changelog/).
