---
title: "Documentation Search Console MCP"
description: "Installer Search Console MCP, connecter Google et Bing, lancer des audits bornés et interpréter les preuves."
lang: fr
lastUpdated: 2026-10-07
canonicalEnglish: /docs/
---

Utilisez Search Console MCP avec Claude, Codex ou un autre assistant IA pour comprendre vos dernières évolutions SEO et obtenir une liste de correctifs priorisés. Posez vos questions en langage courant, sans expertise SEO requise : « Analyse les performances récentes de mon site et dis-moi quoi corriger en priorité. »

Le serveur récupère les métriques de recherche et audite les pages ; votre assistant explique les variations de trafic, repère les opportunités de classement et propose des changements sur les titres, le contenu, les liens internes ou le SEO technique. Connectez vos comptes une fois, validez les propositions, puis relancez l’analyse pour mesurer leur effet. Les contrôles récurrents demandent une automatisation du client ou un planificateur, et les gains de classement ne sont pas garantis.

## Choisissez votre point d’entrée

| Votre problème | Ouvrir le parcours | Ce que vous obtenez |
| --- | --- | --- |
| Je débute en SEO : par où commencer ? | [Faire le point et comprendre quoi analyser](/fr/#seo-getting-started) | Un état des lieux, trois priorités et quoi mesurer |
| Mon trafic baisse | [Analyser les évolutions](/fr/#seo-traffic) | Un diagnostic et les pages concernées, avec les métriques observées |
| Je veux mieux me positionner | [Repérer les opportunités](/fr/#seo-rankings) | Une liste de correctifs priorisés |
| Mes pages sont peu visibles | [Vérifier l’indexation et la technique](/fr/#seo-indexing) | Les problèmes détectés et les correctifs proposés |

Chaque parcours contient un prompt à copier dans Claude ou Codex, les données nécessaires et un exemple de résultat. Le texte copié demande à l’assistant d’utiliser Search Console MCP et de vérifier sa connexion avant l’analyse. Il inclut les liens vers l’installation, la connexion Google et le scénario GitHub correspondant pour guider la configuration manquante. Remplacez le site d’exemple avant l’envoi du prompt.

Si vous débutez en SEO, choisissez le premier parcours. Votre assistant explique quoi analyser, comment interpréter les résultats et quelles métriques suivre. Vous pouvez commencer avec les pages publiques ; connectez Google Search Console pour mesurer les performances de recherche. GA4 et Bing sont facultatifs.

<figure class="docs-visual">
  <img src="/images/docs/search-evidence-map.webp" width="1376" height="768" alt="Trois flux de preuves séparés convergent vers un espace d’analyse borné." loading="eager" fetchpriority="high">
  <figcaption>Les preuves Google, Bing et des pages publiques restent distinctes dans un même espace d’analyse borné.</figcaption>
</figure>

## Commencez par 1 de ces 5 tâches

1. [Installer le serveur](/fr/docs/installation/) sans lancer plusieurs processus persistants.
2. [Connecter Google](/fr/docs/google-setup/) et vérifier les propriétés accessibles.
3. [Connecter Bing](/fr/docs/bing-setup/) en distinguant la clé de compte de la clé IndexNow.
4. [Lancer un prompt](/fr/docs/prompts/) ou choisir un [scénario guidé](/fr/docs/examples/).
5. [Interpréter les preuves](/fr/docs/evidence-and-safety/) avant toute action d’écriture.

## Preuves retournées par 3 sources

Le serveur expose des réponses de fournisseurs, des données de pages publiques et des calculs rattachés à une fenêtre explicite. Une soumission acceptée prouve uniquement que le fournisseur a accepté la demande. Elle ne prouve ni le crawl ni l’indexation ultérieure.

<div class="provider-boundaries" role="list" aria-label="Fournisseurs de preuves">
  <div role="listitem"><strong>Google</strong><span>Performances, inspection, GA4 et CrUX lorsqu’ils sont configurés.</span></div>
  <div role="listitem"><strong>Bing</strong><span>Performances Webmaster, crawl, feeds, backlinks et soumissions bornées.</span></div>
  <div role="listitem"><strong>Pages publiques</strong><span>HTML, robots, sitemaps, métadonnées, schémas et liens internes.</span></div>
</div>

## Code source et historique des versions

Consultez l’[architecture](/fr/docs/architecture/), le [résumé des versions](/fr/docs/changelog/) ou le [dépôt source](https://github.com/FlorianBruniaux/google-search-console-mcp).

[Lire la version anglaise canonique](/docs/).
