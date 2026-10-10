---
title: "Évaluation hors ligne des requêtes et paires"
description: "Évaluer des prédictions fournies contre des annotations indépendantes depuis un checkout source."
lang: fr
lastUpdated: 2026-10-10
canonicalEnglish: /docs/classifier-evaluation/
---

Les évaluateurs de ce guide sont des scripts non publiés du dépôt, pas des commandes installées par le wheel 1.5.0. Utilisez Python 3.11 ou ultérieur depuis un [checkout source](/fr/docs/bounded-native-audit/#checkout-source-et-prérequis). L’évaluateur des requêtes utilise seulement la bibliothèque standard ; il n’ajoute aucun outil MCP public, et la découverte par défaut reste à 96 outils.

`scripts/eval_classifier.py` valide les annotations de l’appelant et des prédictions indépendantes, puis rapporte leur qualité hors ligne. Il utilise la bibliothèque standard Python, n’importe aucun classifieur et n’appelle aucune API. #6 reste ouverte jusqu’à l’obtention d’annotations humaines FR/EN autorisées, d’un corpus held-out figé et de cibles convenues. Les fichiers de `tests/fixtures/classifier_eval/` sont des exemples synthétiques de limites et ne satisfont pas cette exigence.

Utilisez la [collecte d’évaluations humaines](/fr/docs/expert-evaluation-intake/) pour attribuer la revue humaine, réunir les preuves de chaque tâche et figer un lot avant réglage. Elle identifie les interfaces existantes et les axes qu’elles ne peuvent pas évaluer.

Le [guide d’audit natif](/fr/docs/bounded-native-audit/#évaluation-humaine-des-rapports) décrit l’interface séparée des affirmations de rapport. L’[extraction du contenu principal](/fr/docs/content-extraction/#comparaison-hors-ligne-avec-annotations) a son propre comparateur local de fragments.

## Taxonomie d’annotation : `query-intent-v1`

Annotez le résultat recherché. La forme interrogative seule ne détermine pas l’intention.

| Label d’intention | Règle d’annotation |
| --- | --- |
| `informational` | Cherche une explication, une procédure ou un fait. |
| `navigational` | Cherche une destination nommée, un compte ou une page connue. |
| `commercial` | Compare ou évalue des options avant de choisir. |
| `transactional` | Cherche à acheter, réserver, télécharger ou effectuer une action concrète. |
| `unclassified` | Le contexte ne permet pas une intention unique, ou plusieurs intentions restent non résolues. |

Conservez négation, qualificatifs et objet de la requête. « Où puis-je acheter… » est une question transactionnelle. Une comparaison sans question peut rester commerciale. N’inférez pas l’intention de la ponctuation ou d’un mot déclencheur. Les annotateurs doivent distinguer la demande d’effectuer une action de la demande d’apprendre son fonctionnement.

Les labels de paire sont `same_intent`, `distinct_intent` et `unclassified`. Jugez si les requêtes cherchent le même résultat précis, plutôt que la seule présence du label large `informational`. Utilisez `unclassified` si la relation ne peut pas être résolue. Conservez `left_id` et `right_id` : « convertir A en B » et « convertir B en A » cherchent des résultats directionnels différents. Inverser l’ordre de ces deux identifiants ne change pas le sens de chaque requête. Le harnais traite `(left_id, right_id)` comme une identité ordonnée et permet son inverse comme annotation distincte.

Ces définitions constituent la taxonomie du cadre. La revue humaine doit les approuver et les figer pour #4/#5 avant réglage. Un changement de taxonomie exige une nouvelle version et une revue du corpus ; le harnais n’accepte actuellement que `query-intent-v1`.

## Autorisation, désaccords et splits

Visez environ 200 requêtes FR/EN autorisées et anonymisées pour la collecte initiale. Ce compte n’établit pas un support held-out suffisant par langue/classe et ne couvre pas les autres tâches de #6 ; les humains doivent convenir séparément de ces exigences. Retirez domaines privés, URLs, identifiants, adresses email et texte identifiant avant import. Conservez les preuves d’autorisation source dans un emplacement approuvé et une référence non identifiante dans chaque annotation. Ne commitez ni sources privées ni identifiants secrets.

Un annotateur humain fournit le label ; un autre relecteur humain vérifie l’ambiguïté et résout les désaccords. Enregistrez la résolution, y compris `no disagreement` si applicable. Un agent ou modèle proposant un label ne doit pas juger sa propre vérité de référence. La CLI refuse des chaînes `annotator` et `reviewer` égales pour les requêtes et paires. Des chaînes distinctes sont seulement un contrôle mécanique ; les métadonnées enregistrent les déclarations de l’appelant. La CLI ne peut établir consentement, qualité d’anonymisation, identité, véritable participation humaine ou chronologie réelle avant réglage.

Attribuez paraphrases, variantes orthographiques, traductions et requêtes liées à un `family_id`. Gardez chaque famille dans un seul split : `train`, `tuning` ou `held_out`. Visez des moitiés tuning/held-out approximativement égales pour le corpus initial ; `train` reste disponible si la référence en a besoin. Les deux membres d’une paire doivent occuper son split. Les paires liées nécessitent la même attribution de famille. Le validateur contrôle les identifiants déclarés et les références ; les humains doivent revoir la carte des familles, car il ne découvre pas un recoupement sémantique non déclaré.

Séparez les labels held-out des entrées de classifieur, prompts et accès de réglage. Les auteurs des prédictions reçoivent les identifiants/textes des requêtes ou les identifiants/membres des paires, sans labels ni jugements d’annotation. Un évaluateur autorisé rapproche prédictions et labels. Le schéma strict refuse les champs de référence dans les prédictions, sans prouver que leur auteur n’a jamais vu ces labels.

## Schéma JSON du corpus

Tous les champs ci-dessous sont obligatoires. Champs inconnus, clés JSON dupliquées et identifiants dupliqués entre les deux tableaux font échouer la validation. Identifiants et références sont des chaînes non vides. Utilisez du JSON UTF-8, `schema_version: 1`, et une provenance par corpus : `human` ou `synthetic`. Les corpus mixtes nécessitent des fichiers et rapports séparés.

```json
{
  "schema_version": 1,
  "corpus_id": "synthetic-schema-example",
  "taxonomy_version": "query-intent-v1",
  "provenance": "synthetic",
  "queries": [
    {
      "id": "q1",
      "family_id": "f1",
      "query": "comment comparer deux solutions",
      "language": "fr",
      "label": "commercial",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    },
    {
      "id": "q2",
      "family_id": "f1",
      "query": "how to compare two solutions",
      "language": "en",
      "label": "commercial",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    }
  ],
  "pairs": [
    {
      "id": "p1",
      "family_id": "pf1",
      "left_id": "q1",
      "right_id": "q2",
      "label": "same_intent",
      "split": "held_out",
      "annotation": {
        "provenance": "synthetic",
        "annotator": "fixture-author",
        "reviewer": "fixture-reviewer",
        "source_authorization": "synthetic example authored for this guide",
        "disagreement_resolution": "controlled example, no human corpus"
      }
    }
  ]
}
```

`queries` et `pairs` sont des tableaux qui peuvent chacun être vides. La tâche et le split sélectionnés doivent contenir au moins un enregistrement. Les langues sont `fr` ou `en`. Chaque champ d’annotation est une chaîne non vide ; sa provenance doit correspondre au corpus. Auto-paires, références absentes, répétition de paires ordonnées et références traversant les splits échouent.

## Schéma JSON des prédictions indépendantes

Les champs principaux sont obligatoires. `task` vaut `intent` ou `pairs` ; `run_kind` vaut `rules` ou `model`. Tâche et split sélectionnent l’ensemble évalué. Identifiants supplémentaires, dans un autre split ou dupliqués échouent. Identifiants absents et prédictions explicitement `null` comptent comme abstentions.

```json
{
  "schema_version": 1,
  "corpus_id": "synthetic-schema-example",
  "run_id": "baseline-v1",
  "run_kind": "rules",
  "task": "intent",
  "split": "held_out",
  "predictions": [
    {
      "id": "q1",
      "predicted_label": "commercial",
      "confidence": 0.8,
      "cost_usd": 0.0,
      "latency_ms": 1.2,
      "scores": {
        "informational": 0.2,
        "navigational": 0.0,
        "commercial": 0.8,
        "transactional": 0.0,
        "unclassified": 0.0
      }
    },
    {"id": "q2", "predicted_label": null}
  ]
}
```

Chaque ligne nécessite seulement `id` et `predicted_label`. Les quatre champs optionnels montrés sont la liste complète. Confiance et scores doivent être finis dans `[0, 1]` ; coût et latence doivent être finis et non négatifs. Les booléens ne comptent pas comme nombres. Les scores nécessitent tous les labels de la tâche, aucun autre, avec une somme de un sous tolérance flottante. Les paires utilisent leurs trois labels. Les scores décrivent la distribution de l’appelant ; la CLI ne remplace ni n’infère `predicted_label` à partir d’eux.

Les champs de référence comme `label`, `expected_label`, les annotations ou le texte des requêtes sont refusés dans les prédictions. Les métadonnées de modèle restent optionnelles pour rendre visibles les mesures manquantes. Une comparaison de modèle nécessite coûts, latences et scores de probabilité observés complets avant revue de publication.

## Figer le corpus et les cibles numériques avant réglage

Sauvegardez le corpus final autorisé, calculez son SHA-256, convenez des cibles numériques par tâche et enregistrez la référence d’approbation dans un manifeste séparé. Revoyez et figez les octets exacts du corpus et du manifeste avant réglage. Conservez le manifeste sous gestion de versions ou dans un autre enregistrement immuable approuvé. Modifier les espaces du corpus change aussi son hash.

```sh
shasum -a 256 data/authorized-intents.v1.json
```

Le manifeste suivant montre le schéma avec des cibles de démonstration. Ces nombres ne sont pas des seuils convenus et ne doivent pas être copiés comme approbation. `frozen_before_tuning` et `approved_by` sont des déclarations qui nécessitent des preuves humaines.

```json
{
  "schema_version": 1,
  "corpus_id": "authorized-intents-v1",
  "taxonomy_version": "query-intent-v1",
  "dataset_sha256": "replace-with-exact-dataset-sha256",
  "frozen_before_tuning": true,
  "approved_by": "replace-with-actual-human-review-reference",
  "thresholds": {
    "intent": {
      "macro_precision": 0.8,
      "macro_recall": 0.8,
      "full_set_accuracy": 0.8,
      "coverage": 0.9,
      "min_support_per_class": 10
    },
    "pairs": {
      "macro_precision": 0.8,
      "macro_recall": 0.8,
      "full_set_accuracy": 0.8,
      "coverage": 0.9,
      "min_support_per_class": 10
    }
  }
}
```

Chaque bloc de cibles fourni nécessite les cinq champs. Les cibles de qualité/couverture sont des nombres finis dans `[0, 1]`. Le support minimal est un entier positif applicable à chaque classe, y compris `unclassified`. La tâche sélectionnée doit avoir un bloc ; les autres sont optionnels. Le manifeste doit correspondre à l’identifiant du corpus, à la taxonomie et au hash exact. La CLI refuse un manifeste sans référence d’approbation non vide ou avec `frozen_before_tuning` différent de `true`.

## Exécuter et interpréter le rapport

Depuis la racine du dépôt, la fixture fournie fonctionne sans paquet supplémentaire ni identifiants :

```sh
python3 scripts/eval_classifier.py \
  --dataset tests/fixtures/classifier_eval/synthetic-boundary.json \
  --predictions tests/fixtures/classifier_eval/synthetic-predictions.json
```

Utilisez vos fichiers autorisés réels pour une comparaison held-out figée :

```sh
python3 scripts/eval_classifier.py \
  --dataset data/authorized-intents.v1.json \
  --predictions data/baseline-intent.held-out.json \
  --manifest data/authorized-intents.v1.manifest.json > intent-report.json
```

Exécutez les prédictions de paires séparément avec `task: "pairs"`. Comparez la meilleure référence par règles et tout modèle optionnel sur la même entrée figée et le même split. Le harnais n’exécute ni référence ni modèle. Pytest par défaut utilise des données synthétiques ; il n’évalue pas de corpus réel et n’appelle aucun modèle.

La CLI écrit le JSON sur stdout et retourne zéro lorsque l’évaluation réussit. Une entrée invalide retourne `2`, écrit `invalid input:` sur stderr et n’émet aucun rapport. Le succès du processus signifie que l’évaluation a tourné, pas que les cibles de publication sont atteintes.

Chaque classe rapporte support, nombre de prédictions, vrais positifs, précision et rappel. Précision : `TP / predicted_count` ; rappel : `TP / support`. Un dénominateur non défini contribue zéro. Les moyennes macro portent sur toutes les classes, y compris celles sans support. L’exactitude complète divise les prédictions correctes par tout l’ensemble sélectionné. La couverture divise les prédictions non nulles par cet ensemble ; les abstentions incluent les lignes manquantes. `unclassified` est une réponse de classe, distincte de l’abstention `null`.

Coûts totaux et latences moyennes portent seulement sur les lignes avec mesures fournies. `observed_count` et `missing_count` conservent le dénominateur complet ; sans mesure, la sortie est `null`, pas zéro. La calibration rapporte la moyenne du score Brier multiclasse, `sum((score - one_hot_label)^2)`, pour les lignes avec vecteurs complets, et les comptes observés/manquants. C’est une mesure d’erreur de probabilité, pas une preuve de calibration sur des populations réelles. La confiance seule ne fournit pas cette mesure.

`release_gate.threshold_assessment.status` vaut `not_supplied`, `not_held_out`, `met` ou `not_met`. Les cibles fournies sont contrôlées uniquement sur `held_out` ; chaque contrôle et cible apparaît dans le rapport. Les hashes du corpus et des prédictions identifient les octets évalués. Un corpus synthétique renvoie toujours `release_gate.status: "ineligible_synthetic"`, même si les cibles sont atteintes. Un corpus déclaré humain renvoie `pending_human_review` ; la CLI n’approuve jamais de publication. Le relecteur doit établir de vrais labels, consentement, isolation des splits, approbation avant réglage et amélioration sur la meilleure référence. Les vraies entrées humaines et cibles convenues manquent encore dans ce cadre.

## Axes futurs séparés

Le corpus de requêtes conditionne intention/regroupement sous #4/#5. Il ne valide pas les autres tâches. Réutilisez les modèles de validation avec schémas, corpus et cibles propres à chaque tâche ; la CLI accepte seulement `intent` et `pairs`.

| Tâche future | Labels humains indépendants et métriques nécessaires |
| --- | --- |
| Avertissements éditoriaux, #17 et brouillons #24 | Passages FR/EN autorisés annotés acceptables, actionnables ou dépendants du contexte par genre ; précision par règle, avertissements actionnables manqués, support par genre et désaccords. Les fixtures HTML établissent seulement le comportement d’implémentation. |
| Fidélité de réécriture, #20 | Paires original/révision revues pour nombres, unités, dates, liens, négation, modalité, référents, périmètre et causalité. Séparer contrôles mécaniques et revue sémantique ; l’agent de réécriture ne juge pas sa propre référence. |
| Similarité des pages, #22 | Jugements sur paires couvrant gabarits partagés, traductions et recoupements légitimes de services locaux. Une similarité candidate n’établit pas une cannibalisation et n’autorise ni fusion ni suppression. |
| Détection d’instructions et readiness | Corpus distincts de pages positives/bénignes et labels par tâche. Les labels de requêtes ou éditoriaux ne valident ni détection d’injection ni probabilité de citation. |

Figez les familles de pages, documents et révisions liés dans un seul split par axe. Enregistrez autorisation, anonymisation, provenance, désaccords et cibles avant réglage. Séparez les rapports pour qu’un agrégat ne masque pas une tâche faible. L’intégration d’un modèle reste optionnelle.

## Axes de preuves d’audit : préparation de #6

Les protocoles suivants préparent #38/#39/#40/#41/#45/#46. Ils n’ajoutent aucune tâche à `scripts/eval_classifier.py`, aucun label humain ni approbation de publication. Utilisez un adaptateur et un rapport séparés par tâche après collecte du corpus autorisé et des cibles figées.

| Axe | Couverture des cas | Question de revue | Mesures à figer avant réglage |
| --- | --- | --- | --- |
| Diagnostic de trafic | Retard de données, lignes absentes, zéro observé, pics historiques, références saisonnières, incidents de collecte et changements déclarés | Quelle affirmation est soutenue, hypothétique ou exige une abstention ? Ne pas inventer la vraie cause. | Affirmations non soutenues, conservation des preuves, abstention justifiée et support par famille |
| Concurrence nuisible | Résultats catégorie/produit légitimes, intention/marché distincts, requêtes navigationnelles, migration et alternance d’URL matérielle | Les preuves justifient-elles une revue ou un changement conditionnel ? Une requête partagée seule ne justifie pas la consolidation. | Fausses consolidations proposées, candidats manqués, intention inconnue et support familial |
| Extraction principale | Pages autorisées FR/EN d’article, produit, service local, forum et coquille JS avec limites gabarit/contenu annotées indépendamment | Quels segments source appartiennent à l’échantillon de la tâche ? L’extracteur candidat ne fournit pas ses propres labels. | Segments de gabarit inclus, segments utiles omis, entrées non prises en charge et changements d’avertissements métier |
| Fidélité des rapports | Paquets multipropriétés, fenêtres incompatibles, fournisseurs partiels, indexation inconnue, observations contradictoires et sortie bornée | Chaque affirmation conserve-t-elle source et incertitude ? L’accord entre modèles ne fournit pas de label humain. | Erreurs source/fenêtre, conversion indisponible-zéro, affirmations non soutenues et omissions avec compte/motif |

### Protocole de paquet et revue

1. Figez le paquet d’un cas avec versions exactes outils/requêtes, site/propriété effectifs, dates demandées/observées, observations, états manquants/erreurs, périmètre de collecte et référence d’autorisation. Conservez le hash original hors du rapport dérivé. Retirez les identifiants privés avant commit.
2. Enregistrez axe, langue et attribution famille/split. Gardez même propriété/événement/page et révisions liées dans une famille pour éviter des fuites d’observations proches vers held-out. Un humain doit vérifier cette attribution ; la déclaration ne prouve pas l’isolation.
3. Pour chaque affirmation, demandez à un annotateur humain les références d’observation et un label soutenu, non soutenu ou non résolu depuis le paquet. Un second humain enregistre désaccords et résolution. Séparez observations et cause sous-jacente inconnue.
4. Figez octets approuvés, définitions, cibles numériques par tâche et référence d’approbation avant réglage. Cibles ou labels revus manquants laissent la qualité en attente ; les sorties synthétiques restent des contrôles d’implémentation.
5. Donnez les observations à l’auteur sans les labels held-out. Un évaluateur rapproche rapport et jugements indépendants. Explicitez comptes et dénominateurs non définis ; aucun score global ne doit masquer un axe faible.

### Cas d’implémentation contrôlés

Les premiers contrôles peuvent utiliser des paquets synthétiques : apparences de recherche génériques sans identification IA vérifiée ; alerte de concentration du trafic sans observation d’action manuelle ; requête légitime multi-URL d’intention inconnue ; inspection absente avec clics nuls mesurés. Ces observations ne doivent pas devenir respectivement une perte IA estimée, une pénalité, une fusion inconditionnelle ou un verdict de non-indexation.

Ce sont des familles de cas proposées, pas des exemples humains collectés ou des essais d’agents exécutés. Scores de routage/BM25, tests de clients simulés et auto-vérification d’un modèle n’établissent pas la précision des rapports. Ce protocole laisse #6 ouverte pour les données autorisées propres à chaque tâche, les labels revus indépendamment et les cibles avant réglage.
