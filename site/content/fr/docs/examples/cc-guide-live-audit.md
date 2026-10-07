---
title: "Analyse réelle du Claude Code Ultimate Guide"
description: "Une exécution réelle de Search Console MCP : mesures Google, audits de pages, recommandations et trace des appels."
lang: fr
lastUpdated: 2026-10-07
canonicalEnglish: /docs/examples/cc-guide-live-audit/
---

Exécution du **2026-10-07** sur [cc.bruniaux.com](https://cc.bruniaux.com/) : 14 appels réels à Search Console MCP depuis Codex, des données Google et trois audits de pages publiques. Cet exemple présente une analyse. Aucun changement n’a été appliqué au site et aucun gain de classement n’a été mesuré.

[Télécharger la trace partageable des requêtes et réponses](/evidence/2026-10-07-cc-guide.json). Elle contient des extraits relus, avec les horodatages, durées, paramètres et résultats expliqués ci-dessous. Les droits d’accès au compte, la configuration des connexions, les métadonnées internes et les requêtes sans rapport avec cet exemple sont omis. Les réponses originales complètes restent privées et ne sont pas incluses dans le site. Ces métriques Search Console sont partagées volontairement pour cet exemple ; ce ne sont pas des données publiques de Google.

## 1. Ce que l’analyse mesure

Du 7 septembre au 4 octobre, le site reçoit **459 clics**, avec un **taux de clic de 0,82 %** et une **position moyenne de 7,3**. Par rapport au 10 août–6 septembre, les clics progressent de **11,95 %** et les impressions de **48,21 %**. La visibilité augmente plus vite que les clics ; cet exemple ne porte pas sur une chute de trafic.

| Recherche web Google | 10 août–6 septembre | 7 septembre–4 octobre |
| --- | ---: | ---: |
| Clics | 410 | 459 |
| Impressions | 37 731 | 55 921 |
| Taux de clic calculé sur les totaux | 1,09 % | 0,82 % |

Un clic est une visite depuis un résultat de recherche. Une impression est une apparition dans les résultats. Le taux de clic correspond aux clics divisés par les impressions. La position moyenne résume de nombreuses recherches ; ce n’est pas le classement d’un mot-clé unique. Les totaux proviennent de données non regroupées par requête, confirmées avec `get_advanced_search_analytics` et `data_state="final"`. Les requêtes visibles ne permettent pas de reconstruire ces totaux.

## 2. Actions proposées

| Priorité | Signal observé | Action proposée | Périmètre | Quoi mesurer |
| --- | --- | --- | --- | --- |
| P1 | `/releases/` : 19 clics pour 12 693 impressions ; deux requêtes visibles sur la dernière version cumulent 936 impressions sans clic | Examiner les extraits de recherche par requête, pays et appareil, puis tester un changement si l’intention observée le justifie | Une page et un test | Clics et taux de clic de ces requêtes, avec impressions et position pour contexte |
| P2 | `/guide/third-party-tools/` : 9 clics pour 7 106 impressions ; des recherches portent sur RTK / lean-ctx | Donner à la comparaison existante un titre descriptif et une entrée dans la table des matières | Un bloc de contenu existant | Clics de la page et taux de clic des requêtes de comparaison, en signalant le faible volume |
| P2 | La même page contient de nombreuses destinations accessibles uniquement par la navigation | Revoir les liens contextuels pertinents, en tenant compte des liens déjà présents dans le contenu et des URL alternatives | Les liens d’une page | Liens dans le contenu et évolution des métriques des pages visées |

L’assistant propose ces actions à partir des données ; elles n’ont pas été testées sur le site. Le benchmark de `quick_wins` sert à classer les pistes. Ses scores calculés ne prédisent pas des visites récupérées.

## 3. Des résultats des outils à une recommandation

### Repérer les pages à examiner

`get_performance_overview` et `compare_search_periods` établissent les deux périodes de 28 jours. `get_search_analytics` donne les métriques par page ; `quick_wins` fait ressortir les pages des versions, des outils tiers et de l’architecture parmi les premières pistes à vérifier.

| Page | Clics | Impressions | Taux de clic | Position moyenne |
| --- | ---: | ---: | ---: | ---: |
| [Versions](https://cc.bruniaux.com/releases/) | 19 | 12 693 | 0,15 % | 7,2 |
| [Outils tiers](https://cc.bruniaux.com/guide/third-party-tools/) | 9 | 7 106 | 0,13 % | 6,8 |
| [Architecture](https://cc.bruniaux.com/guide/architecture/) | 8 | 5 231 | 0,15 % | 6,2 |

### Vérifier l’intention et la page avant de proposer une réécriture

`get_search_by_page_query` trouve 485 impressions sans clic pour « latest claude code version » sur `/releases/`, et 451 pour « claude code latest version ». L’audit technique trouve un titre cohérent avec cette intention, une description, une URL canonical correcte et aucun blocage dans robots.txt. La lecture de la page confirme qu’elle explique déjà la dernière version en haut du contenu. La prochaine étape est d’examiner les extraits de recherche ; aucun titre manquant ni résumé de version absent n’a été trouvé.

Sur la page des outils, deux requêtes visibles de comparaison RTK / lean-ctx cumulent 27 impressions sans clic. La lecture de la page confirme que cette comparaison existe déjà dans la section lean-ctx. La proposition consiste à rendre cette réponse plus facile à trouver. Le volume de ces requêtes est trop faible pour promettre un gain.

### Revoir les alertes automatiques

`heading_audit` trouve un H1 et aucun saut de hiérarchie sur chacune des deux pages du guide. La page des outils possède 74 titres, même si l’outil signale une alerte faible sur le nombre de mots par H2. Il faut examiner les sous-titres existants avant d’en ajouter.

`internal_links_audit` trouve 47 liens dans le contenu et 106 destinations accessibles uniquement depuis des zones de navigation sur cette page. Cela ne démontre pas 106 pages orphelines dans le site. Les audits techniques signalent aussi trois en-têtes de sécurité absents par page. Ce sont des pistes de durcissement ; cette exécution n’établit pas qu’ils causent un mauvais classement. Aucun problème HTML critique n’a été retourné pour les trois pages auditées.

## 4. Ce que cette exécution ne vérifie pas

L’engagement et les conversions GA4, Bing, les Core Web Vitals terrain, les concurrents, les backlinks et l’indexation Google n’ont pas été mesurés. Aucun appel à URL Inspection n’a été effectué. Une réponse HTTP 200 et un robots.txt accessible ne prouvent pas l’indexation. L’audit technique porte sur trois pages.

La trace conserve le fait que `row_limit` n’a pas limité deux réponses : 354 lignes de pages et 1 399 lignes page/requête ont été retournées. La trace publique conserve les trois pages et uniquement les quatre requêtes expliquées dans ce cas. Les listes complètes de titres et de liens, les empreintes des logs privés et les détails du dépôt sont également omis. La construction du site n’accepte que cet export relu ; toute modification demande une nouvelle revue de confidentialité. La version du paquet MCP est `UNKNOWN` ; 81 outils disponibles ont été observés. Les logs sont des extraits des appels MCP, pas une capture réseau ni les logs internes du serveur.

Après un changement choisi, collectez une nouvelle période équivalente de 28 jours et comparez la page et les requêtes concernées. Conservez le contexte des recherches et des autres changements ; une différence avant/après ne prouve pas à elle seule un lien de cause à effet. Pour reproduire l’analyse, utilisez le [scénario d’audit rapide](/fr/docs/examples/quick-audit/) et les paramètres de la trace.

Action suivante : examiner les extraits des deux requêtes sur la dernière version avant de choisir un changement sur `/releases/`.
