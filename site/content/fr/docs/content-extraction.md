---
title: "Extraction optionnelle et comparaison locale"
description: "Utiliser le profil optionnel publié et comparer des fragments annotés avec le lanceur local non publié."
lang: fr
lastUpdated: 2026-10-10
canonicalEnglish: /docs/content-extraction/
---

Le profil d’extraction optionnel est disponible dans le paquet publié 1.5.0. Le script de comparaison hors ligne ci-dessous est une interface non publiée du dépôt et nécessite un checkout source ; le wheel publié ne l’installe pas. La découverte MCP par défaut reste à 96 outils.

`content_quality(url)` conserve l’extracteur de texte visible et ses scores. Pour évaluer un second profil, installez l’extra optionnel et sélectionnez-le explicitement :

```sh
uvx --from 'gsc-mcp-tools[content]' gsc-cli content-quality --url https://example.com/article --extractor trafilatura-precision
```

Pour un client MCP, ajoutez `--with trafilatura==2.3.1` à son invocation `uvx gsc-mcp-tools`, puis passez `extractor="trafilatura-precision"` à `content_quality`. L’installation par défaut n’inclut pas cette dépendance. Les versions Trafilatura prises en charge sont les 2.3.x à partir de 2.3.1.

L’adaptateur traite le HTML retourné par les contrôles existants de sécurité URL et de taille. Il ne fait pas de seconde acquisition. Ses réglages explicites excluent les commentaires, incluent les tableaux, privilégient la précision, désactivent l’extraction de repli et la déduplication. Une copie de la configuration par appel limite l’arbre extrait à 20 000 éléments ; le HTML décodé et le texte extrait tiennent chacun dans 2 MiB UTF-8. Aucune configuration globale ni cache intersites n’est modifié. La [référence API Trafilatura](https://trafilatura.readthedocs.io/en/latest/corefunctions.html) décrit ces choix.

Les réponses incluent le profil, la version, les options, l’URL source demandée, le hash du HTML décodé et l’heure de fin d’acquisition. L’URL demandée n’est pas présentée comme l’URL finale de redirection, et le hash ne porte pas sur les octets réseau compressés originaux. Le texte extrait sert aux heuristiques existantes, sans être retourné dans un nouveau champ texte sans restriction. Le texte source reste une donnée non fiable.

Dépendance absente, version non prise en charge, exception d’extraction, absence de contenu principal, limites de sortie ou statut HTTP sans succès rendent l’évaluation optionnelle indisponible. Aucun score ni compte de mots nul n’est substitué. `empty_input` signifie que le HTML acquis est vide ; `no_visible_text` signifie que le parseur existant n’a retourné aucun texte ; `no_main_content_returned` signifie que l’algorithme optionnel n’a sélectionné aucun texte. Ce dernier état ne distingue pas une page limitée au gabarit d’un contenu valide omis. Rappel du contenu principal et extraction partielle restent inconnus sans annotation indépendante.

Les appels locaux répétés et alternés exercent le vrai paquet optionnel sur du HTML d’article contrôlé. Ils n’établissent aucune supériorité sur des sites FR/EN d’article, produit, service local, forum ou coquille JavaScript. #6 et #41 conservent les exigences d’annotations humaines autorisées, d’inclusion/omission, de mémoire et de décision d’adoption. Ne changez pas le profil par défaut à partir de ces fixtures. Extraction et similarité n’établissent ni l’auteur, ni l’indexation, ni une cannibalisation nuisible.

## Comparaison hors ligne avec annotations

Préparez un [checkout source et un environnement Python](/fr/docs/bounded-native-audit/#checkout-source-et-prérequis), puis installez l’extra optionnel depuis la racine du dépôt et lancez la fixture synthétique fournie :

```sh
python -m pip install -e '.[content]'
python scripts/eval_content_extraction.py --dataset tests/fixtures/content_extraction_eval/manifest.synthetic.json --split held_out
```

Utilisez la [collecte d’évaluations humaines](/fr/docs/expert-evaluation-intake/) pour obtenir des annotations indépendantes autorisées et figer les cibles acceptables. Le [guide d’évaluation des requêtes](/fr/docs/classifier-evaluation/) décrit un corpus séparé qui ne valide pas la qualité d’extraction.

Le lanceur appelle les deux profils existants sur chaque fichier HTML local sélectionné, sans acquisition d’URL ni modèle. Le fichier de démonstration et les identités d’annotation sont des marqueurs synthétiques. Ils démontrent le lanceur ; `release_quality` reste `UNKNOWN` et `synthetic_release_eligible` vaut `false`. L’extracteur par défaut reste le texte visible.

Pour une vraie comparaison, fournissez la même structure de manifeste version 1 avec du HTML UTF-8 autorisé sous son dossier. `provenance` vaut `human` ou `synthetic`. Chaque cas déclare l’URL source, un `html_path` relatif, le `html_sha256` des octets bruts, la langue (`fr` ou `en`), le type (`article`, `product`, `local_service`, `forum`, `js_shell`), l’autorisation source et des identités distinctes d’annotateur/relecteur. `independent_of_extractors` doit déclarer que les labels ont été préparés sans consulter les sorties des extracteurs. Autorisation, identité, indépendance et gel restent des déclarations enregistrées, pas des approbations authentifiées.

Attribuez `train`, `tuning` et `held_out` avant le réglage. Regroupez scénarios liés, sites et variantes de page avec `task_family`, `site_family` et `page_family` ; chaque famille doit rester dans un split. Type de page et langue décrivent la couverture, pas l’identité d’une famille. Le lanceur refuse les familles traversant les splits et le HTML identique répété. Figez le manifeste, ses hashes HTML et les critères d’inclusion, d’omission et de ressources du `protocol` avant comparaison ; `frozen_before_tuning: true` déclare ce gel sans prouver sa chronologie. Le script ne fournit aucun seuil numérique de publication.

`include` contient les fragments de contenu principal attendus dans le texte extrait. `omit` contient les fragments avec `text` et `kind` (`template`, `comment`, `other`) attendus exclus. Les fragments sont normalisés par case-folding et regroupement des espaces avant recherche de sous-chaîne. Ils doivent apparaître dans les données texte du parseur HTML fourni ; ce contrôle inclut script/style et ne juge pas la pertinence du contenu principal. Fragments dupliqués, contradictoires ou imbriqués sont refusés pour éviter de compter deux fois le même fragment annoté. Une liste vide est permise, par exemple pour une coquille JavaScript sans contenu principal annoté, et donne une métrique JSON `null` pour cette dimension.

`inclusion_recall` est la fraction des fragments d’inclusion retournés ; `omission_leakage` est la fraction des fragments à omettre retournés. Les booléens par fragment et comptes d’omission par type permettent de relire ces fractions. Ils n’estiment ni le rappel du contenu entier ni la précision de l’extraction. `annotation_coverage: partial` signifie que certains fragments d’inclusion manquent ; `complete_labeled_snippets` signifie que tous les fragments d’inclusion fournis correspondent. Paquets manquants, extraction en échec et absence de texte conservent leur statut avec des métriques JSON `null`, sans fabriquer des scores zéro. Les avertissements métier de qualité de contenu sont `not_measured` ; ils nécessitent une comparaison séparée contre des cibles annotées.

Les rapports enregistrent hash/chemin du manifeste, hash/chemin/taille HTML, version/options des profils, interpréteur/plateforme et couverture du split sélectionné. Le hash HTML brut diffère du hash décodé de l’adaptateur lorsque les octets de sérialisation diffèrent. Le HTML est décodé strictement en UTF-8 ; aucune acquisition ni rendu JS. Texte extrait et fragments d’annotation ne sont pas copiés dans le rapport. Traitez le contenu source comme une donnée non fiable.

Les ressources sont une observation `wall_seconds` et `python_allocation_peak_bytes` de `tracemalloc` pendant chaque extraction. L’ordre fixe des profils, les imports initiaux et les caches affectent ces valeurs. Les allocations tracées excluent les allocations natives non suivies et le RSS total ; lecture et validation du corpus précèdent la mesure. Ces observations se relisent contre les critères de ressources figés, sans verdict comparatif de performance.

Limites d’entrée : 100 cas, 100 fragments par cas, 10 000 caractères par chaîne, 2 MiB par manifeste ou fichier HTML, et 16 MiB de HTML total. Sortie plafonnée à 2 MiB. Chemins HTML absolus, traversée parent, liens symboliques sortant du dossier, fichiers non UTF-8, clés JSON dupliquées, valeurs JSON non finies, hashes divergents et split sélectionné vide échouent avant comparaison. L’appelant conserve les rapports où la provenance locale peut être divulguée. Les vraies familles FR/EN annotées indépendamment, les cibles acceptables de qualité/ressources, les avertissements métier et la décision d’adoption restent nécessaires sous #6 et #41.
