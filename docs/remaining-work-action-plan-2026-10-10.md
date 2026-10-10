# Search Console MCP : travail restant et plan d’action

État vérifié le 10 octobre 2026. Périmètre : backlog global du dépôt, outils, agents, évaluation et site. Les priorités ci-dessous sont une recommandation, pas des fonctionnalités déjà réalisées.

## État de référence

- `main` local et distant : `28e8e4ad47fc5fa9db3bcb1cbd3471958abc5b2b`.
- Version du code : 1.5.0. La connexion MCP active renvoie 96 outils, en mode toutes les familles. Le décalage historique à 85 outils est donc résolu pour cette connexion. Cette découverte ne vérifie ni les credentials Google, ni une requête Bing, ni le comportement des agents.
- GitHub : 19 tickets ouverts, aucune PR ouverte dans la réponse collectée. #10 est le ticket de suivi ; les 18 autres couvrent correctifs, fonctions et validations.
- Les correctifs du retour d’Alexandre sont livrés, tickets #28 à #34 fermés. Son retest terrain reste à obtenir.
- Les pages par profil, le catalogue et le menu compact sont intégrés. Aucun ticket site ouvert ne figure dans ce backlog. Cela ne vaut pas audit exhaustif du site.
- Les imports SiteOne, leur stockage local et leurs rapprochements, les différences de crawl, les logs locaux, la matrice d’observations d’indexation et les références de trafic sont livrés. #37, #40, #43, #44, #46 et #48 sont fermés.
- Trafilatura est déjà disponible en option ; les playbooks partagés et le pilote d’agents sont déjà implémentés. Leurs tickets restent ouverts pour des validations ou extensions précises.

Les fichiers de recherche et handoff non suivis présents dans le checkout ont été conservés. Aucune implémentation, modification de ticket, publication ou modification de configuration globale n’a été réalisée pour ce récapitulatif.

## Inventaire complet des tickets ouverts

| Ticket | État réel et reste à faire | Priorité proposée |
|---|---|---|
| [#74](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/74) | Correctif absent : une ligne manquante dans la comparaison Google/Bing retourne encore des zéros numériques. Retourner `null`, conserver les vrais zéros et les limites de comparaison. | A1 |
| [#38](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/38) | Playbooks corrigés et partagés. Reste à exécuter les cas dans les clients natifs et à évaluer les conclusions avec des humains. | A2 et A3 |
| [#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39) | Pilote contrôlé livré. Reste : adaptateur natif, rôles par client, budget au niveau des appels réels aux fournisseurs, observations immuables partagées et validation des rapports. | A2 et A3 |
| [#6](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/6) | Guide et évaluateur hors ligne livrés. Manquent les exemples autorisés, annotations humaines, jeux de validation séparés et seuils convenus avant réglage. Des adaptateurs d’évaluation propres aux autres tâches restent à créer. | A3, à commencer en parallèle |
| [#41](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/41) | Extracteur Trafilatura optionnel livré. Comparer inclusion/omission du contenu et ressources sur des pages FR/EN annotées avant toute adoption par défaut. | A4 |
| [#42](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/42) | Partie SiteOne complète. Reste l’adaptateur Unlighthouse, après obtention d’un export réel versionné avec appareil, configuration et échantillon. | A4 |
| [#49](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/49) | Imports SERP et backlinks absents. Définir deux schémas distincts, provenance et couverture, puis valider des exports représentatifs autorisés. | A4 |
| [#53](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/53) | Import local GSC Bulk Export absent. Gérer tables, agrégations, données anonymisées, partitions et révisions ; rapprocher seulement les fenêtres compatibles. Connecteur BigQuery direct hors première livraison. | A4 |
| [#45](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/45) | Extension temporelle de la cannibalisation absente : parts matérielles et alternance d’URL. Publication soumise aux cas humains spécifiques de #6. | A5 |
| [#5](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/5) | Classification FR/EN de l’intention absente. Commencer par des règles explicables, conserver les non-classés et distinguer forme interrogative et intention. | A5 |
| [#4](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/4) | Regroupement approché de requêtes absent. Conserver le mode exact ; produire des candidats avec variantes et motifs, sans fusionner silencieusement les sens. | A5 |
| [#22](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/22) | Comparaison des passages de pages absente. Il faut des paires humaines autorisées, les passages responsables des rapprochements et une couverture bornée. | A5 après validation de l’extraction |
| [#47](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/47) | Le descriptif avant/après existe. Manquent le registre local des changements et le protocole de suivi avec contrôles. Nécessite des cohortes et une revue méthodologique adaptées. | A6, conditionnel |
| [#52](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/52) | La carte de liens existe. Extension aux graphes importés et métriques relatives à l’échantillon seulement si une décision montre leur utilité. | A6, conditionnel |
| [#50](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/50) | Fédération de recherche absente. Vérifier les interfaces des corpus et relier chaque affirmation à un passage effectivement consulté. | A6, conditionnel |
| [#9](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/9) | Signaux de préparation à la citation absents. Une grille explicable et une décision d’évaluation doivent précéder tout score ; aucune probabilité de citation ne peut être revendiquée. | A6, différé |
| [#7](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/7) | Backend de classification absent. Choisir un seul backend optionnel seulement après un bénéfice démontré face aux règles ; budget, reprises et coûts doivent être bornés. | A6, différé |
| [#51](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/51) | Collecteur persistant absent. Ne l’ouvrir qu’après un manque mesuré des imports/fetchs actuels, puis tester interruption, reprise, robots et ressources. | A6, différé |
| [#10](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/10) | Suivi du programme. Actualiser les preuves et clôturer uniquement quand les critères restants sont satisfaits. | Transversal |

## Plan d’action ordonné

### A1. Corriger les données absentes dans la comparaison Google/Bing

C’est le premier changement : son périmètre est borné et il évite qu’un agent lise une absence comme une mesure de zéro trafic. Le code actuel confirme le défaut dans `_missing_metrics()` et conserve le libellé `zero_filled_with_present_false`.

1. Écrire les régressions pour absence côté Google, absence côté Bing, vrais zéros et paires comparables.
2. Remplacer les valeurs manquantes par `null`. Un CTR avec dénominateur nul reste indisponible ; les comptes nuls réellement observés restent `0`.
3. Vérifier les consommateurs, métadonnées et deltas. Ne pas créer de delta de position entre moteurs.
4. Synchroniser documentation EN/FR et changelog, vérifier le paquet puis les contrôles distants lors de la livraison.

Fichiers de départ :

- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/search_compare.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/tests/test_search_compare.py`
- `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/evidence.py`

Validation de sortie : valeurs et preuves cohérentes, vrais zéros préservés, deltas suspendus pour données absentes ou fenêtres incompatibles. Taille relative : petite.

### A2. Terminer l’exécution native et les budgets des agents

Commencer par un client réellement disponible et une propriété explicitement sélectionnée. La présence de 96 outils est vérifiée ; l’exécution des rôles et le respect des budgets fournisseurs restent à établir.

1. Décrire le contrat de lancement et les capacités du client choisi. Implémenter le premier adaptateur natif, puis la projection des rôles correspondante.
2. Compter les tentatives physiques aux frontières Google/Bing/GA4, y compris erreurs, reprises et appels concurrents, sous un budget partagé.
3. Partager des observations immuables entre spécialistes pour éviter les acquisitions répétées. Le partage de données dans un prompt ne suffit pas à garantir ce comportement.
4. Exécuter les cas de fournisseur indisponible, propriété incompatible, absence de page, indexation inconnue et budget épuisé.
5. Conserver une revue distincte et le brouillon non approuvé. Valider le second client séparément lorsqu’il est disponible.

Fichiers de départ : `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/.claude/workflows/mega-audit.js`, `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/.claude/agents/` et `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/providers/`. Le chemin du nouvel adaptateur dépendra du contrat natif retenu.

Validation de sortie : traces du client natif, budgets testés sur erreurs/reprises/concurrence, identité des observations préservée jusqu’au rapport. Une vérification de signatures ou une simulation ne suffit pas à clôturer le comportement natif. Taille relative : grande.

### A3. Obtenir et exploiter les cas experts en parallèle

Cette étape fournit les données qui débloquent les conclusions et classifications. Elle peut avancer pendant A1 et A2.

1. Obtenir le retest d’Alexandre et, avec son accord, des cas/exportations anonymisés. Son retest valide des cas d’usage ; il ne remplace pas tous les jeux d’évaluation.
2. Prioriser les cas de diagnostic de trafic, de fidélité des rapports et de concurrence entre pages. Ajouter les pages annotées nécessaires à l’extraction.
3. Approuver les catégories et seuils avant réglage ; garder les variantes d’un même site, événement ou document dans la même partition.
4. Faire annoter et résoudre les désaccords indépendamment du système évalué. Créer les adaptateurs propres aux tâches : l’évaluateur existant accepte les intentions et paires de requêtes, pas tous les audits.
5. Publier erreurs, abstentions et effectifs par tâche. Évaluer séparément requêtes, passages de pages, extraction et rapports.

Fichiers de départ : `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/docs/classifier-evaluation.md` et `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/scripts/eval_classifier.py`.

Validation de sortie : entrées autorisées, labels humains, séparation figée et seuils préalables pour chaque tâche évaluée. Dépendance externe : données et revue humaine. Aucun exemple synthétique ne clôture cette exigence.

### A4. Étendre les preuves disponibles sans nouvelle acquisition obligatoire

Ordre proposé : évaluer Trafilatura (#41), ajouter Unlighthouse (#42), importer SERP/backlinks (#49), puis GSC Bulk Export (#53). Cet ordre peut changer si un export autorisé est disponible plus tôt ; ces trois adaptateurs ne dépendent pas les uns des autres.

- #41 : comparaison sur contenu utile annoté, bruit de template et ressources. Conserver le profil actuel par défaut tant que les critères d’adoption ne passent pas.
- #42 : inspecter un export réel avant d’écrire l’adaptateur. Conserver appareil, configuration, échantillon et distinction entre laboratoire et terrain.
- #49 : livrer des schémas séparés pour SERP et backlinks, avec locale, appareil, date et limites du producteur.
- #53 : commencer par des fichiers locaux. Vérifier calculs pondérés, partitions absentes, révisions et répétition d’import sans double comptage. Aucun SDK/cloud payant n’est nécessaire à cette première version.

Réutiliser `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/crawl_snapshots.py` et `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/content_extraction.py` selon la tâche, sans faire passer les nouveaux types de données pour des observations de crawl.

Validation de sortie : un export représentatif autorisé par producteur, schémas versionnés, couverture explicite, limites d’entrée et tests de doublons/incompatibilités. Taille relative : moyenne à grande, par adaptateur.

### A5. Ajouter les analyses SEO après leurs validations propres

Ordre produit proposé : concurrence temporelle (#45), intention des requêtes (#5), regroupement approché (#4), puis passages similaires entre pages (#22).

Ce n’est pas une chaîne de dépendances techniques : #45 n’exige pas #4, et aucun des trois premiers ne nécessite un backend de modèle. Les tâches peuvent être développées séparément dès que leurs cas sont prêts. Chaque publication attend son propre gate #6 ; #22 attend ses paires de pages et la qualité d’extraction adaptée.

Validation de sortie : motifs et passages inspectables, variantes originales conservées, agrégations sans double comptage, inconnues et abstentions visibles, performances mesurées sur les cas tenus à l’écart du réglage. Aucune similarité ou alternance d’URL ne suffit à recommander une fusion ou suppression.

Fichiers de départ : `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/seo.py`, `/Users/florianbruniaux/Sites/perso/google-search-console-mcp/src/gsc_mcp/tools/content.py` et le registre partagé. Taille relative : moyenne, par analyse.

### A6. Garder les extensions conditionnelles hors du prochain lot

- #47 : ouvrir le registre et suivi contrôlé lorsqu’un changement réel, des contrôles défendables et une métrique permettent le protocole. Le descriptif avant/après existe déjà.
- #52 : demander une décision précise que la carte actuelle ne permet pas avant d’ajouter centralité, profondeur ou graphes comparés.
- #50 : intégrer un corpus à la fois après vérification de son interface et d’un passage consultable. Une découverte bibliographique n’est pas une mesure du site.
- #9 : définir d’abord l’usage d’une grille de préparation ; conserver les signaux séparés, sans prétendre prédire les citations.
- #7 : attendre un gain mesuré face aux règles sur une tâche nommée avant le premier backend et son budget.
- #51 : attendre un besoin enregistré de reprise, de taille ou de rendu que les imports actuels ne couvrent pas avant tout nouveau crawler.

## Contrôle commun à chaque livraison

Régression ciblée, tests affectés puis suite d’intégration appropriée ; contrats de métadonnées et registre ; documentation canonique/FR ; contrôle du paquet et du site si affectés. Après intégration, distinguer commit, CI, publication et validation terrain. Mettre à jour #10 et les tickets concernés avec les preuves exactes, sans clôturer les critères humains ou natifs à partir de fixtures.

Premier lot recommandé : A1, cadrage du premier adaptateur A2 et préparation des paquets A3. Le travail humain A3 avance en parallèle. Les exports A4 peuvent être recueillis indépendamment. A5 attend ses jeux de validation ; A6 reste conditionnel.

## Sources et limites

Backlog GitHub ouvert et fermé relu pendant cette session ; commit distant vérifié ; comparaison inspectée dans le code ; `get_capabilities` appelé sur la connexion active. Le ticket [#10](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/10) et les notes d’exécution des tickets partiellement livrés ont été croisés avec les sources.

Les nombres de tests historiques et preuves de release proviennent des rapports existants, sans nouvelle exécution de ces suites. Aucun nouvel audit Google/Bing/GA4, test natif d’agent ou contrôle du site public n’a été exécuté pour ce plan. Les checklists initiales de certains tickets restent non cochées malgré leurs livraisons partielles ; leurs notes d’exécution donnent un état plus précis.

## Exécution après autorisation

Le correctif A1, les chemins natifs Codex et Claude sur observations hors ligne et leur acquisition bornée, l’évaluateur de rapports A3 et les prototypes hors ligne A5 ont été implémentés dans une branche isolée. Les validations effectuées et les entrées encore nécessaires figurent dans [le bilan d’exécution](validation/2026-10-10-backlog-execution.md). Les limites ci-dessus décrivent l’état au moment du récapitulatif ; ce bilan porte les preuves plus récentes.
