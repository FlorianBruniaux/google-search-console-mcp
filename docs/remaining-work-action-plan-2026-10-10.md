# Search Console MCP : plan d’action restant

Backlog réconcilié le 10 octobre 2026 après les PR #76 et #77. Ce document remplace le récapitulatif antérieur et ses tâches désormais livrées. Il décrit du travail restant, sans estimation de durée.

## Livré et sorti du plan

- Retours d’Alexandre corrigés (#28 à #34), sélection des familles d’outils et correction des métriques absentes dans la comparaison Google/Bing (#74).
- Site bilingue avec parcours par profil, menu compact, catalogue des 96 outils, documentation, changelog et sitemaps.
- Preuves de rapport, références de trafic, analyse locale de logs, imports SiteOne versionnés et rapprochements, différences de crawl et matrice d’observations d’indexation.
- Playbooks partagés Claude/Codex corrigés : #38 est clos, ses essais interactifs restants sont transférés à #39 et sa validation humaine à #6.
- Acquisition immuable, budgets persistants aux frontières des appels, adaptateurs natifs, neuf profils de revue des sources, concurrence bornée et synthèse suivie d’une invocation de revue séparée.
- Extracteur Trafilatura disponible en option ; guide et évaluateurs hors ligne des requêtes/rapports ; prototypes FR/EN d’intention et de variantes de requêtes.

Les preuves techniques sont dans [le bilan du premier lot](validation/2026-10-10-backlog-execution.md) et [le bilan des spécialistes natifs](validation/2026-10-10-native-specialists.md). Les profils natifs relisent les sources fournies ; ils n’exécutent pas les playbooks interactifs et ne constituent pas un audit technique complet.

Référence source des livraisons : `84a9bd18cf3bd16a1f5b7d8f05f1e412e8615ebb`, fusion de la [PR #77](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/77), après la [PR #76](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/76). Les bilans enregistrent 2 013 tests Python et 113 tests navigateur. Codex et Claude ont chacun exécuté deux spécialistes, une synthèse et une revue hors ligne : quatre appels natifs, deux appels d’outil et zéro tentative fournisseur par essai. Ces résultats n’établissent ni accès authentifié aux fournisseurs, ni qualité SEO experte. La version publiée du paquet reste 1.5.0 ; les derniers changements n’ont pas fait l’objet d’une nouvelle publication PyPI.

## Ordre d’exécution

### A1. Constituer les cas experts et figer les critères, P1

Ticket [#6](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/6). Les outils d’évaluation existent : collecter les entrées autorisées et faire annoter les cas indépendamment du système évalué.

1. Choisir les cas FR/EN de fidélité des rapports, diagnostic de trafic et concurrence entre pages ; préparer séparément le corpus de requêtes et les annotations HTML.
2. Définir pour chaque tâche les labels, les familles de séparation et les seuils avant réglage. Conserver les variantes d’un même site, événement ou document dans une même partition.
3. Recueillir les annotations humaines, résoudre les désaccords et préparer des entrées d’auteur sans labels de validation.
4. Exécuter les évaluateurs compatibles ; ajouter un adaptateur uniquement lorsqu’un schéma de tâche le demande. Publier erreurs, abstentions et effectifs par tâche.

Sortie : cas autorisés, provenance des annotations, jeux tenus à l’écart du réglage, cibles figées et résultats inspectables. Apport : mesurer ce que les diagnostics savent soutenir et leurs erreurs, plutôt que déduire la qualité du nombre de tests.

Fichiers de départ :

- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/docs/classifier-evaluation.md`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/scripts/eval_classifier.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/scripts/eval_audit_reports.py`

### A2. Valider le parcours réel et les playbooks interactifs, P1

Ticket [#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39), qui reprend les scénarios non terminés de #38. Réutiliser les adaptateurs et budgets déjà implémentés.

1. Sélectionner explicitement une propriété GSC, des URL, les fenêtres et les périmètres Bing/GA4 lorsque nécessaires.
2. Exécuter l’acquisition authentifiée dans le runner installé ; conserver les traces des tentatives, de la réutilisation des observations, des sources et des branches indisponibles.
3. Exécuter séparément les playbooks interactifs dans chaque client : retards/chutes de trafic, résultats multi-URL légitimes, indexation inconnue, preuves IA absentes, fournisseurs ou familles d’outils indisponibles et dimensions Bing non prises en charge.
4. Tester les affirmations non soutenues sur pénalités, pertes causales IA et consolidation ; mesurer la revue sur les cas A1.
5. Borner les écritures de sortie des processus natifs pendant leur exécution. Les plafonds actuels des rapports conservés et les contrôles après retour ne bornent pas la croissance du disque pendant l’appel.
6. Définir l’acquisition HTML/CrUX nécessaire avant toute extension. Le rôle schema reste indisponible dans le runner actuel sans source adaptée ; aucune source ne doit être inventée pour compléter le rapport.

Sortie : preuves propres à chaque client/fournisseur, états partiels conservés et conclusions évaluées avec A1. Apport : passer d’un parcours hors ligne démontré à des usages réels documentés. Les compteurs d’appels ne sont pas des plafonds de coût monétaire ; la concurrence est bornée par pipeline.

Fichiers de départ :

- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/audit_runtime.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/native_audit.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/native_roles.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/scripts/run_bounded_audit.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/docs/bounded-native-audit.md`

A1 et A2 peuvent avancer en parallèle. Le retest d’Alexandre peut fournir des cas avec son accord ; il ne remplace pas les jeux de validation indépendants.

### A3. Évaluer l’extraction et ajouter les imports disponibles, P2

| Ticket | Reste à livrer | Entrée et critère de sortie | Apport |
|---|---|---|---|
| [#41](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/41) | Comparaison qualité/ressources du profil Trafilatura existant et décision d’adoption | HTML FR/EN annoté indépendamment, critères préalables d’inclusion/omission ; comparaison avec l’extracteur actuel | Moins de bruit de template dans les audits de contenu |
| [#42](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/42) | Adaptateur Unlighthouse sur le contrat d’import livré | Export réel versionné, appareil/configuration/échantillon ; mesures de laboratoire et terrain distinctes | Observations de performance sur plusieurs pages |
| [#49](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/49) | Adaptateurs distincts SERP et backlinks | Exports autorisés avec producteur, locale, appareil, dates et couverture ; compatibilité démontrée par format | Contexte concurrentiel et liens externes inspectables |
| [#53](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/53) | Import local GSC Bulk Export et rapprochements compatibles | Tables site/URL représentatives, données anonymisées, partitions/révisions ; agrégation sans double comptage | Préserver l’historique fourni et expliquer les écarts compatibles avec l’API |

Ces adaptateurs ne dépendent pas les uns des autres. Recueillir les exports pendant A1/A2 ; commencer celui dont l’entrée réelle est disponible. Le connecteur BigQuery facturé reste hors première livraison. SiteOne ne valide pas le format d’un autre producteur, et aucun import ne crée d’historique antérieur absent.

Fichiers de départ : `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/content_extraction.py` et `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/crawl_snapshots.py`.

### A4. Publier les analyses après leurs évaluations propres

| Ticket | Reste à livrer | Sortie attendue et apport |
|---|---|---|
| [#45](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/45), P2 | Parts matérielles de trafic et alternance des URL dans le temps | Cas quotidiens revus et critères préalables ; réduire les faux positifs de cannibalisation |
| [#5](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/5), P2 | Évaluation du prototype d’intention livré et intégration d’un rapport borné | Qualité par classe, abstentions et agrégats corrects ; guider la priorisation éditoriale |
| [#4](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/4), P2 | Évaluation du prototype de variantes livré et sortie candidate opt-in | Variantes/motifs conservés, absence de double comptage, défaut exact inchangé ; rapprocher des requêtes à examiner |
| [#22](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/22), P3 | Similarité des passages sur des paires de pages annotées | Passages responsables du rapprochement et limites d’extraction ; montrer les recouvrements concrets |

Chaque tâche utilise ses propres labels A1. Ni le partage d’une requête, ni la similarité d’un texte ne justifie seul une fusion, une redirection ou une suppression. Aucun backend de modèle n’est obligatoire pour ces premières versions.

Fichiers de départ : `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/query_rules.py`, `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/scripts/query_rules_baseline.py`, `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/seo.py` et `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/content.py`.

## Extensions différées, hors prochain lot

| Ticket | Condition pour ouvrir l’implémentation | Apport recherché |
|---|---|---|
| [#47](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/47) | Changement déclaré, contrôles crédibles et protocole relu indépendamment | Suivi des modifications au-delà du descriptif avant/après livré |
| [#52](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/52) | Graphe importé et décision que la carte actuelle ne permet pas | Examiner accessibilité et pages sous-liées dans l’échantillon observé |
| [#50](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/50) | Corpus autorisé pertinent et interface de récupération vérifiée | Appuyer les recommandations sur des passages consultés |
| [#9](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/9) | Décision de préparation d’une page et protocole d’évaluation explicites | Exposer des signaux inspectables sans prédire les citations IA |
| [#7](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/7) | Gain mesuré sur une tâche nommée face aux règles, coût et empreinte bornés | Ajouter un seul backend de classification optionnel utile |
| [#51](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/51) | Manque mesuré de collecte, reprise ou rendu dans les imports/fetchs existants | Ajouter un collecteur persistant seulement lorsque nécessaire |

## Suivi et règles de clôture

[#10](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/10) porte ce même ordre. Après nettoyage : 17 issues ouvertes, dont ce suivi et 16 chantiers fonctionnels ou d’évaluation. #38 est clos avec transfert explicite de ses critères d’exécution à #39 et de qualité à #6. Les autres tickets restent séparés parce qu’ils ont des entrées ou décisions distinctes ; aucune nouvelle issue n’est nécessaire pour conserver leur périmètre.

Clôturer sur les preuves du périmètre livré, ou transférer explicitement les critères restants avant une clôture par regroupement. Les tests de contrat, la CI, le paquet installé, les modèles natifs, les accès fournisseurs et le site public ne sont pas interchangeables. Les chiffres de validation ci-dessus sont ceux des bilans existants ; ce nettoyage n’a pas réexécuté les suites ni acquis des données fournisseurs.
