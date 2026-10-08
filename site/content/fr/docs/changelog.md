---
title: "Historique des versions"
description: "Résumé français des versions de Search Console MCP et lien vers l’historique canonique."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/changelog/
---

Cette page résume les changements utiles aux utilisateurs. L’[historique anglais](/docs/changelog/) reste la source exhaustive.

## Non publié

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
