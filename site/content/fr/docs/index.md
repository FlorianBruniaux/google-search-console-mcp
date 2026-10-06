---
title: "Documentation Search Console MCP"
description: "Installer Search Console MCP, connecter Google et Bing, lancer des audits bornés et interpréter les preuves."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/
---

Search Console MCP réunit les données de Google Search Console, Bing Webmaster Tools, GA4 et CrUX en option, ainsi que les signaux des pages publiques.

<figure class="docs-visual">
  <img src="/images/docs/search-evidence-map.webp" width="1376" height="768" alt="Trois flux de preuves séparés convergent vers un espace d’analyse borné." loading="eager" fetchpriority="high">
  <figcaption>Les preuves Google, Bing et des pages publiques restent distinctes dans un même espace d’analyse borné.</figcaption>
</figure>

## Choisir votre prochaine étape

1. [Installer le serveur](/fr/docs/installation/) sans lancer plusieurs processus persistants.
2. [Connecter Google](/fr/docs/google-setup/) et vérifier les propriétés accessibles.
3. [Connecter Bing](/fr/docs/bing-setup/) en distinguant la clé de compte de la clé IndexNow.
4. [Lancer un prompt](/fr/docs/prompts/) ou choisir un [scénario guidé](/fr/docs/examples/).
5. [Interpréter les preuves](/fr/docs/evidence-and-safety/) avant toute action d’écriture.

## Ce que le serveur peut prouver

Le serveur expose des réponses de fournisseurs, des données de pages publiques et des calculs rattachés à une fenêtre explicite. Une soumission acceptée prouve uniquement que le fournisseur a accepté la demande. Elle ne prouve ni le crawl ni l’indexation ultérieure.

<div class="provider-boundaries" role="list" aria-label="Fournisseurs de preuves">
  <div role="listitem"><strong>Google</strong><span>Performances, inspection, GA4 et CrUX lorsqu’ils sont configurés.</span></div>
  <div role="listitem"><strong>Bing</strong><span>Performances Webmaster, crawl, feeds, backlinks et soumissions bornées.</span></div>
  <div role="listitem"><strong>Pages publiques</strong><span>HTML, robots, sitemaps, métadonnées, schémas et liens internes.</span></div>
</div>

## Source et versions

Consultez l’[architecture](/fr/docs/architecture/), le [résumé des versions](/fr/docs/changelog/) ou le [dépôt source](https://github.com/FlorianBruniaux/google-search-console-mcp).

[Lire la version anglaise canonique](/docs/).
