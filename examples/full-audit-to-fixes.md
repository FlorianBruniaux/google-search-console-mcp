# Full SEO Audit and GitHub Fix Workflow

Copy the French prompt below into the project to audit. It requests a complete SEO audit, a GitHub epic and issues before any corrective change, followed by implementation and validation. Provider access, costs and publication permissions remain subject to verification. This is a reusable prompt, not an executed audit.

## Prompt à copier

Réalise un audit SEO complet de ce projet et de son site, puis enchaîne les correctifs identifiés jusqu’à leur validation. **Crée une epic GitHub et toutes les issues issues de l’audit avant de commencer les corrections.**

Je veux une exécution complète : acquisition des preuves, diagnostic, publication du backlog, implémentation et vérification. Ne termine pas après avoir présenté le plan.

## 1. Identifier le périmètre et l’état initial

Lis les instructions du projet, les skills applicables et sa documentation. Inspecte le dépôt avant toute modification.

Établis :

- Le dépôt GitHub concerné, la branche active, le commit de départ et les modifications locales présentes.
- Le domaine de production, les variantes du domaine et les environnements de prévisualisation.
- Les sources qui font autorité pour le code, les contenus, les métadonnées et les fichiers générés.
- Le framework, le mode de rendu, les principaux types de pages et les langues.
- Le fonctionnement du build, de la CI et du déploiement.
- Les propriétés Search Console, GA4 et Bing correspondant réellement au site.
- Les objectifs du site, les pages stratégiques et les conversions documentées.

Déduis ces informations des sources disponibles. Pose une question seulement lorsqu’une ambiguïté empêche de choisir le bon périmètre ou de poursuivre une action autorisée.

Préserve les modifications existantes. N’écrase, ne réinitialise et ne supprime aucun travail tiers.

## 2. Mobiliser l’intégralité des outils disponibles

**Inventorie l’intégralité des outils, connecteurs, MCP, skills, commandes et capacités de navigateur à ta disposition. Utilise tous ceux qui apportent une preuve ou une vérification pertinente pour cet audit.**

Ne limite pas le travail à la lecture du code ou à un seul scanner. Combine les sources disponibles :

- Analyse du dépôt, de ses générateurs et de ses configurations.
- Crawl du site et inspection des réponses HTTP.
- Navigateur réel pour le rendu, les interactions et les captures.
- Google Search Console et inspection d’URL.
- GA4 et Bing Webmaster Tools.
- Lighthouse, PageSpeed Insights et CrUX.
- Outils de SERP, de mots-clés, de concurrence, de backlinks et de visibilité dans les moteurs IA.
- Exports de crawl et journaux serveur accessibles.
- GitHub pour les issues, PR et résultats de CI.
- Tests, linters, vérifications de types et build du projet.

Utilise notamment le MCP SEO/GSC lorsqu’il est disponible. Commence par découvrir ses capacités réelles, puis vérifie les propriétés accessibles et leur correspondance avec le domaine audité.

Pour DataForSEO, SerpApi, Ahrefs ou tout autre fournisseur, vérifie la disponibilité effective, les accès, les quotas et le coût avant l’acquisition. Respecte les budgets déjà autorisés. Une configuration présente ne prouve pas que le fournisseur fonctionne.

Produis une matrice de couverture indiquant, pour chaque capacité :

- Son rôle dans l’audit.
- Les outils utilisés et les résultats obtenus.
- Les accès manquants ou les échecs.
- La raison de sa non-utilisation, le cas échéant.
- Les limites de couverture et leur conséquence sur les conclusions.

L’exigence d’utiliser tous les outils concerne les capacités pertinentes. Elle n’autorise pas les appels sans rapport avec le site, les dépenses supplémentaires ou les mutations externes pendant l’acquisition.

Si la délégation est disponible, répartis les volets indépendants entre agents avec des responsabilités explicites. Consolide leurs preuves et leurs conclusions. Évite les modifications concurrentes sur les mêmes fichiers.

## 3. Capturer les preuves avant de corriger

Réalise d’abord l’audit en lecture seule. Enregistre les preuves dans un dossier dédié, en séparant les données brutes, les analyses et les captures.

Pour chaque acquisition, conserve :

- La source, l’outil et la date de collecte.
- Le domaine, la propriété ou l’environnement interrogé.
- La période, les filtres et les dimensions.
- Les limites demandées, la pagination et les volumes réellement retournés.
- La couverture, les erreurs et la fraîcheur des données.

Distingue systématiquement :

- **PROUVÉ** : constat directement vérifiable.
- **PARTIEL** : constat établi sur un échantillon ou une partie du périmètre.
- **DÉCLARÉ** : information documentée mais non vérifiée.
- **UNKNOWN** : information absente, inaccessible ou contradictoire.

N’invente ni métrique, ni score, ni cause, ni gain attendu. Une absence de données ne signifie pas une absence de trafic ou de problème.

N’intègre aucun secret ni donnée privée dans une issue publique, une capture publiée ou un fichier versionné. Publie les preuves nécessaires sous une forme expurgée.

## 4. Auditer tous les volets applicables

### Exploration, indexation et architecture

Vérifie :

- Les codes HTTP, les erreurs, les soft 404 et les pages inaccessibles.
- Les redirections, leurs chaînes, leurs boucles et leurs destinations.
- Les variantes HTTP/HTTPS, avec/sans www, slash, casse et paramètres.
- Les directives robots, les balises d’indexation et les en-têtes associés.
- Les sitemaps, leurs index, leur contenu et leur cohérence avec les pages canoniques.
- Les canonicals, les doublons et les contradictions entre signaux.
- La pagination, les facettes et les espaces d’URL susceptibles de multiplier les pages.
- Le rendu serveur, le rendu JavaScript et la disponibilité du contenu et des liens.
- Les pages orphelines, la profondeur et la structure de navigation.
- Les états d’indexation observés dans Google et Bing.
- Les journaux de crawl lorsqu’ils sont disponibles.

Réconcilie les URL découvertes dans le code, le crawl, les sitemaps et les données des moteurs. Ne confonds pas absence dans Search Analytics, absence du sitemap et absence d’indexation.

### Métadonnées et contenu

Examine chaque gabarit et les pages stratégiques :

- Titres, descriptions, H1 et hiérarchie des titres.
- Métadonnées manquantes, dupliquées ou incohérentes.
- Correspondance entre contenu, intention de recherche et promesse de la page.
- Contenus pauvres, répétitifs, obsolètes ou contradictoires.
- Exactitude des affirmations, identité des auteurs et sources.
- Lisibilité et cohérence éditoriale.
- Prévisualisations sociales lorsque pertinentes.

Ne réécris pas systématiquement les contenus pour satisfaire un score. Préserve les faits, les conditions, les chiffres et les engagements.

### Maillage interne et médias

Contrôle :

- Liens cassés, liens redirigés et destinations non canoniques.
- Ancres et placement des liens.
- Navigation, breadcrumbs et parcours vers les pages stratégiques.
- Répartition des liens entre pages et gabarits.
- Formats, dimensions, poids et chargement des images.
- Textes alternatifs selon leur fonction.
- Vidéos et autres médias lorsqu’ils participent au référencement.

### Données structurées

Vérifie :

- La syntaxe et les propriétés requises.
- La correspondance avec le contenu visible.
- La cohérence des entités et de leurs identifiants.
- Les duplications et contradictions entre blocs.
- L’éligibilité aux fonctionnalités recherchées, selon les règles actuelles.

Distingue validité syntaxique, conformité et affichage effectif dans les résultats.

### Performance et expérience utilisateur

Analyse :

- LCP, INP et CLS lorsque les données existent.
- TTFB, ressources bloquantes, JavaScript et CSS.
- Images responsables du LCP, polices et scripts tiers.
- Cache, compression et chargement différé.
- Hydratation et stabilité visuelle.
- Comportement mobile, navigation et parcours de conversion.
- Accessibilité affectant l’utilisation du site.

Sépare les mesures de laboratoire des données terrain. Inspecte les causes avant de proposer une correction.

### Recherche organique et comportement

Avec les propriétés vérifiées, analyse :

- Des périodes comparables récentes et plus longues.
- Les clics, impressions, CTR et positions.
- Les pages et requêtes, avec leur rapprochement.
- Les segments pertinents par appareil, pays et type de recherche.
- Les pertes, anomalies, concentrations et possibilités d’amélioration.
- Les requêtes proches des premières positions.
- La concurrence entre pages pour une même intention.
- Les pages d’entrée organiques, l’engagement et les conversions.

Respecte les délais de remontée, les limites de lignes et les différences de définition entre fournisseurs. Les clics Search Console et les sessions GA4 ne sont pas interchangeables.

Une baisse ne prouve pas sa cause. Plusieurs pages visibles sur une requête ne prouvent pas une cannibalisation nuisible.

### SERP, concurrence et visibilité IA

Lorsque les outils et les données le permettent :

- Vérifie les intentions et les formats des résultats sur les requêtes prioritaires.
- Compare le site aux concurrents réellement observés.
- Identifie les lacunes de contenu et de couverture.
- Examine les backlinks et les domaines référents.
- Vérifie les éléments favorisant la compréhension, l’attribution et la citation des contenus.
- Consigne les mentions ou citations observées dans les surfaces IA.

Précise le moteur, la requête, la localisation, la langue et la date. N’extrapole pas une observation isolée à une visibilité générale.

### Volets conditionnels

Audite également, lorsqu’ils s’appliquent :

- Internationalisation, hreflang et cohérence entre langues.
- SEO local et informations d’établissement.
- Produits, catégories, variantes et données commerciales.
- Articles, actualités et Discover.
- Sites générés, contenus synchronisés et dépôts multiples.

Justifie les volets non applicables.

### Implémentation et chaîne de livraison

Relie les défauts observés aux sources qui les produisent :

- Templates et composants.
- Générateurs et synchronisations.
- Configuration du framework et de l’hébergement.
- Routage, en-têtes, cache et génération des sitemaps.
- Tests existants et contrôles de CI.

Corrige les sources qui font autorité. Une modification manuelle d’un fichier généré ne constitue pas une correction durable si la prochaine génération l’efface.

## 5. Consolider le diagnostic et le plan

Produis un rapport complet et un plan d’action avant l’implémentation.

Attribue un identifiant stable à chaque constat. Documente :

- Le problème observé et son périmètre.
- Les preuves et leur niveau de confiance.
- Les URL, gabarits, fichiers et systèmes concernés.
- La cause vérifiée ou les hypothèses restant à tester.
- L’impact et la priorité.
- Le correctif proposé et ses alternatives utiles.
- Les dépendances.
- Les critères d’acceptation.
- Les tests ou vérifications nécessaires.
- La réversibilité et les risques de régression.

Priorise selon l’impact, les preuves et les dépendances. Regroupe les symptômes partageant la même cause lorsqu’un correctif commun les traite.

Pour les hypothèses insuffisamment établies, prévois une investigation avec ses propres critères de sortie. Ne transforme pas une hypothèse en correction automatique.

Exprime le périmètre en étapes, fichiers et systèmes touchés. Ne fournis aucune estimation de durée sans données de calibration.

## 6. Créer l’epic et toutes les issues avant les correctifs

**Cette étape doit être terminée avant la première modification corrective.**

Vérifie les issues et les PR existantes pour éviter les doublons. Réutilise ou complète les tickets qui couvrent déjà les constats.

Crée une epic GitHub contenant :

- Le périmètre et les objectifs.
- Les liens vers le rapport et le plan.
- La couverture et les limites de l’audit.
- La liste complète des issues enfants.
- Leur ordre d’exécution et leurs dépendances.
- Les critères de clôture de l’epic.

Utilise les relations parent/enfant natives si elles sont disponibles. Sinon, maintiens des liens réciproques et une checklist.

Crée une issue pour chaque unité de travail, avec :

- Un titre décrivant le résultat attendu.
- Les identifiants des constats couverts.
- La priorité et le niveau de preuve.
- Le problème, sa reproduction et les preuves expurgées.
- Le périmètre technique et les sources à modifier.
- La solution proposée.
- Les dépendances et les exclusions.
- Les critères d’acceptation vérifiables.
- Les tests, la validation et le retour arrière.
- Les accès ou décisions manquants.
- Un lien vers l’epic.

Vérifie la création effective et conserve les URL. Chaque action du plan doit correspondre à une issue.

Si un nouveau défaut apparaît pendant l’implémentation, crée ou complète son issue et rattache-la à l’epic **avant de le corriger**.

Si GitHub est inaccessible, prépare les tickets et poursuis les investigations possibles. Signale précisément le blocage ; des fichiers locaux ne constituent pas des issues publiées.

## 7. Enchaîner les correctifs

Une fois le backlog publié, commence l’implémentation sans demander de nouvelle confirmation pour chaque correction couverte par cette mission.

Procède par issue et dans l’ordre des dépendances :

1. Reproduis le problème.
2. Définis la vérification qui démontrera sa résolution.
3. Ajoute un test de régression pertinent lorsque le comportement le justifie.
4. Applique le plus petit changement qui traite la cause.
5. Vérifie le résultat et l’absence de régression.
6. Mets à jour l’issue et l’epic avec les preuves.
7. Poursuis avec l’issue suivante.

Pour les modifications de contenu, effectue une comparaison avant/après qui préserve le sens. Pour les corrections de templates, vérifie les pages générées et les autres gabarits concernés.

Ne supprime, ne fusionne, ne redirige ou ne passe en noindex une page sur la seule base d’un score ou d’un trafic non observé. Documente les données, les conséquences et les autorisations nécessaires.

Continue les travaux indépendants lorsqu’une issue est bloquée. N’abandonne pas le programme à cause d’un accès manquant sur un seul volet.

## 8. Valider à chaque niveau

Exécute les contrôles adaptés au projet :

- Tests ciblés et suites pertinentes.
- Lint et vérification des types.
- Build de production.
- Inspection des pages et fichiers générés.
- Crawl de contrôle.
- Vérifications HTTP et navigateur.
- Contrôle des métadonnées, canonicals, robots, sitemaps et données structurées.
- Comparaison des performances lorsque les conditions de mesure sont comparables.
- Revue des changements et résultats de CI lorsque disponibles.

Documente les commandes, résultats et artefacts utiles. Un test qui cherche seulement une chaîne dans le code ne prouve pas le comportement rendu.

Distingue :

- Correction locale validée.
- Correction publiée sur une branche.
- PR ouverte et CI validée.
- Correction intégrée.
- Correction déployée et vérifiée publiquement.
- Effet observé dans les moteurs ou les analytics.

N’affirme jamais qu’un build réussi prouve le déploiement ou qu’un déploiement prouve un gain SEO.

## 9. Respecter les autorisations de publication

Cette mission autorise l’audit, la création de l’epic et des issues, les corrections dans le dépôt et leurs vérifications.

Pour les commits, push, PR et déploiements, applique les autorisations déjà établies dans ce projet. Prépare le travail jusqu’au résultat concret et vérifiable avant de demander une autorisation encore manquante. Ne redemande pas une autorisation déjà donnée.

N’effectue aucune fusion, dépense supplémentaire, suppression externe, modification de compte, soumission de sitemap ou notification d’indexation sans autorisation correspondante.

Après une publication autorisée, rapporte immédiatement son identifiant et vérifie son résultat. Ne contourne aucun contrôle de sécurité ou de CI pour obtenir un statut vert.

## 10. Livrer un état final traçable

Conserve :

- Le profil du site et la matrice des outils.
- Le manifeste des preuves.
- Le rapport d’audit et le plan d’action.
- Les liens vers l’epic et toutes les issues.
- Les résultats de validation.
- La correspondance entre constats, issues, corrections et publications.

Termine par un compte rendu indiquant :

- Les problèmes confirmés et les hypothèses écartées.
- Les corrections effectuées.
- Les vérifications réussies ou échouées.
- Les issues terminées, en cours et bloquées.
- Les commits, branches et PR lorsqu’ils existent.
- L’état du déploiement lorsqu’il a été autorisé.
- Les observations différées restant nécessaires.
- Les décisions ou accès précis encore attendus.

Clôture les issues et l’epic uniquement lorsque leurs critères sont effectivement satisfaits. Si une partie reste bloquée, laisse son état et sa prochaine action explicites.

**Commence maintenant par l’inventaire du projet et des outils. Termine l’audit, publie l’epic et le backlog complet, puis exécute les correctifs jusqu’à épuisement du travail autorisé et réalisable.**
