---
title: "Historique des versions"
description: "Résumé français des versions de Search Console MCP et lien vers l’historique canonique."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/changelog/
---

Cette page résume les changements utiles aux utilisateurs. L’[historique anglais](/docs/changelog/) reste la source exhaustive.

## Non publié

- Ajout de `search_change_breakdown` pour des fenêtres Google explicites, dimensions indépendantes, couverture et résidus descriptifs (#21).
- Ajout de `link_targets_audit` pour les statuts GET des destinations internes et leurs redirections, avec les ancres source (#19). Transport indisponible et erreur HTTP observée restent distincts.
- Le registre source compte désormais 85 outils ; le paquet 1.2.0 publié reste à 81. Le [guide bilingue des audits bornés](/fr/docs/audit-workflows/) documente les appels et limites ; l’évaluation des classifieurs reste dans la documentation contributeur.

- Ajout de `editorial_audit`, profil éditorial FR/EN versionné avec extraits localisés et consignes de réécriture fidèle (#17). Les citations, le code et les exceptions de genre sont protégés. Aucun score d’écriture IA ou de classement.
- Le registre source compte 83 outils ; `content_quality` conserve son API et son score. Le paquet 1.2.0 publié reste à 81 outils.

- Ajout de `ga4_ai_referrals` pour les visites attribuées aux sources d’assistants documentées. Le registre source compte 82 outils ; le paquet publié 1.2.0 en conserve 81. Les candidats restent exclus des totaux confirmés et une couverture insuffisante empêche le calcul de parts.
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
