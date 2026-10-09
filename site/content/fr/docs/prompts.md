---
title: "Prompts de démarrage"
description: "Prompts bornés pour auditer un site, comparer les moteurs et diagnostiquer l’indexation."
lang: fr
lastUpdated: 2026-10-09
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

## Tester la 1.4.0 sans accès fournisseur

La version 1.4.0 expose 89 outils par défaut. Une sélection de familles au démarrage peut en exposer moins ; consultez l’[installation](/fr/docs/installation/). Ce test utilise du texte synthétique et ne vérifie pas l’accès Google ou Bing.

```text
Utilise Search Console MCP pour un test local en lecture seule.
1. Appelle get_capabilities et vérifie la présence de editorial_audit,
   rewrite_fidelity_check, search_weekday_reference, seo_change_impact et crawl_import_preview.
   Signale les outils absents et les restrictions de familles au démarrage.
2. Appelle editorial_audit avec text="Le hic ? Le texte est à relire.",
   language="fr", format="plain". Présente le statut, la couverture et les alertes retournées.
3. Appelle rewrite_fidelity_check avec original="Le rapport couvre 12 pages.",
   revised="Le rapport couvre 20 pages.", language="fr", format="plain".
   Inspecte les changements de nombres et leurs emplacements dans les deux textes.
4. Conserve les métadonnées des résultats et distingue tests réussis, échecs et inconnues.
   N’appelle pas Google/Bing, ne récupère aucune page et ne modifie ni ne publie rien.
Un résultat mécanique sans alerte ne certifie ni la vérité ni la fidélité sémantique.
```

Les [workflows éditoriaux](/fr/docs/editorial-workflows/) donnent les bornes d’entrée et les champs de résultat.

## Comparer les mêmes jours de semaine

Remplacez la propriété par la vôtre. Ce contrôle nécessite un accès Google observé.

```text
Utilise search_weekday_reference pour sc-domain:example.com avec days=28,
max_requests=20 et limit=10. Vérifie d’abord l’accès à cette propriété Google exacte.
Présente les dates effectives, les jours de semaine, la couverture, l’état de données
 demandé, les clics et impressions. Laisse les métriques absentes ou incompatibles indisponibles.
La comparaison décrit les fenêtres observées ; n’en déduis ni saisonnalité annuelle ni cause.
N’effectue aucune écriture.
```

## Suivre une modification déclarée

Fournissez l’événement réel, l’URL et sa date, puis confirmez des fenêtres avant/après explicites de même durée.

```text
Utilise seo_change_impact pour examiner une modification que je déclare.
Avant l’appel, demande la propriété Google, l’URL exacte, la date de l’événement,
sa description et les changements simultanés connus si ces informations manquent.
Propose des fenêtres avant/après égales et disjointes, puis attends ma confirmation.
Conserve le statut d’événement déclaré, la couverture et les métriques disponibles.
Sépare variations mesurées et hypothèses ; ne prétends pas que ma modification a causé un gain.
Ne conserve pas l’événement et n’effectue aucune écriture.
```

## Prévisualiser un export de crawl

Fournissez un export SiteOne JSON sans identifiants secrets. Les fixtures de forme exporteur valident l’adaptateur ; un export réel reste un contrôle distinct.

```text
Utilise crawl_import_preview sur l’export JSON SiteOne que je fournis, avec producer="siteone".
Si je n’ai pas fourni d’export, demande-le plutôt que d’en inventer un.
Présente les nombres acceptés, rejetés et omis, les déclarations du producteur,
la couverture, les empreintes et les erreurs. Les scores importés restent des heuristiques
 du crawler et ne sont pas des signaux de classement.
Ne lance aucun crawler, ne récupère aucune URL, ne lis aucun fichier, n’installe rien,
ne conserve pas les données et ne joins pas GSC.
```

Les [audits bornés](/fr/docs/audit-workflows/) détaillent les contrats des fenêtres, événements et imports.
