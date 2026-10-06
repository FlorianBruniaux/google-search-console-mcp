---
title: "Prompts de démarrage"
description: "Prompts bornés pour auditer un site, comparer les moteurs et diagnostiquer l’indexation."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/prompts/
---

Remplacez les valeurs entre chevrons et demandez d’abord une lecture seule. Le serveur doit conserver le fournisseur, la propriété et la fenêtre avec chaque conclusion.

## Audit rapide

```text
Analyse <site_url> sur les 28 derniers jours. Commence par vérifier les propriétés accessibles. Résume les clics, impressions, CTR et positions sans extrapoler au-delà des données observées. Liste ensuite trois vérifications techniques publiques. N’effectue aucune action d’écriture.
```

## Comparer Google et Bing

```text
Compare la visibilité de <site_url> dans Google Search Console et Bing Webmaster Tools sur des fenêtres comparables. Garde les métriques et les sémantiques de position séparées. Signale les données absentes comme UNKNOWN et propose les contrôles suivants.
```

## Chute de trafic

```text
Compare les 28 derniers jours aux 28 jours précédents pour <site_url>. Sépare requêtes, pages, appareils et pays. Cherche les plus fortes contributions à la variation. Ne présente aucune corrélation comme une cause prouvée.
```

## Indexation

```text
Pour les URL de <sitemap_url>, distingue les états soumis, explorés et indexés. Inspecte un échantillon borné. Propose des actions, mais demande ma confirmation avant toute soumission.
```

## Contenu

```text
À partir des données observées pour <site_url>, identifie les requêtes proches de la première page et les pages associées. Prépare un brief qui sépare les faits GSC des recommandations éditoriales.
```

Retrouvez les versions complètes dans les [scénarios guidés](/fr/docs/examples/).

[Lire la version anglaise canonique](/docs/prompts/).
