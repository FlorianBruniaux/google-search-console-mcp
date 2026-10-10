---
title: "Collecte d’évaluations humaines"
description: "Recueillir des annotations autorisées par tâche et figer les cibles sans fabriquer d’approbation de qualité."
lang: fr
lastUpdated: 2026-10-10
canonicalEnglish: /docs/expert-evaluation-intake/
---

Cette fiche contributeur et ses évaluateurs décrivent un travail non publié du dépôt. Les scripts nécessitent un [checkout source](/fr/docs/bounded-native-audit/#checkout-source-et-prérequis) ; le wheel 1.5.0 seul ne les fournit pas. Le catalogue public par défaut reste à 96 outils. Le [guide d’audit natif](/fr/docs/bounded-native-audit/) couvre l’exécution et ses limites de ressources séparément de la revue humaine de qualité.

La prochaine entrée est un lot humain autorisé, revu indépendamment, avec des cibles figées par tâche. Cette fiche attribue le travail sans fournir labels, seuils ou approbations. Les évaluateurs existants tournent hors ligne ; aucun nouveau harnais ni backend de modèle payant n’est nécessaire pour commencer la collecte.

## Choisir la tâche et son interface

Séparez rapports et comptes de support de chaque tâche. Un succès sur une ligne ne peut pas approuver une autre tâche.

| Tâche | Interface existante | Évaluation prise en charge et limite restante |
| --- | --- | --- |
| Intention des requêtes, #5 | `scripts/eval_classifier.py`, `task: "intent"` | Requêtes FR/EN sous `query-intent-v1` ; précision/rappel/support par classe, exactitude, couverture et abstention. Les cibles fournies peuvent être contrôlées sur `held_out` ; revue humaine de publication encore attendue. |
| Paires de requêtes, #4 | Même CLI, `task: "pairs"` | Labels distincts `same_intent`, `distinct_intent` et `unclassified`. Les deux membres existent dans le corpus et occupent le split de la paire. L’accord sur l’intention large seul ne fournit pas son label. |
| Fidélité de rapport/comportement natif, #39 | `scripts/eval_audit_reports.py`, `track: "report_fidelity"` | Labels d’affirmations fournies contre des observations référencées. Exécution du client natif, preuves omises, analyse de prose libre et seuils numériques de publication ne sont pas évalués. |
| Diagnostic de trafic | Même CLI, `track: "traffic_diagnosis"` | Fondement des affirmations depuis le paquet, y compris inconnu contre zéro et interprétations conditionnelles. N’établit ni cause sous-jacente ni complétude du diagnostic. |
| Concurrence nuisible, #45 | Même CLI, `track: "harmful_competition"` | Fondement des propositions fournies de revue/consolidation. Ne dérive pas l’intention des pages, n’établit pas le préjudice et n’autorise pas une fusion. |
| Extraction principale, #41 | `scripts/eval_content_extraction.py` ; [comparaison d’extraction](/fr/docs/content-extraction/#comparaison-hors-ligne-avec-annotations) | NON PRIS EN CHARGE par les deux CLIs ci-dessus. Le lanceur séparé compare des fragments d’inclusion/omission annotés indépendamment dans du HTML local lié par SHA ; sans estimer rappel du contenu entier ni précision. Vraies annotations humaines, cibles figées et revue des avertissements métier restent nécessaires. |
| Avertissements éditoriaux et fidélité de réécriture | Adaptateur par tâche nécessaire | NON PRIS EN CHARGE par les deux CLIs. Recueillir avertissements actionnables par règle/genre et jugements original/révision ; contrôles littéraux séparés des jugements sémantiques. |
| Similarité de pages, #22 | Adaptateur par tâche nécessaire | NON PRIS EN CHARGE par les deux CLIs. Recueillir labels de paires couvrant gabarits partagés, traductions et similarités locales légitimes. Les labels de paires de requêtes ne les remplacent pas. |
| Détection d’instructions et readiness, #9 | Adaptateur par tâche nécessaire | NON PRIS EN CHARGE par les deux CLIs. Recueillir séparément cas de pages positifs/bénins et labels ; aucun score de requête n’implique une probabilité de citation. |
| Suivi contrôlé, #47 | Protocole et adaptateur par tâche nécessaires | NON PRIS EN CHARGE par les deux CLIs. Revoir estimand/protocole, simulations, échecs de pré-tendance/contamination et observations non concluantes. |
| Recherche documentaire, #50 | Adaptateur par tâche nécessaire | NON PRIS EN CHARGE par les deux CLIs. Revoir passages consultés, pertinence, périmètre abstract/texte intégral, intérêt commercial et formulation fondée sur les sources. |

L’évaluateur de rapports accepte seulement `supported`, `unsupported` et `unresolved`. Une affirmation non résolue est un label sémantique, pas une prédiction absente. La sortie actuelle contient totaux, exactitude, couverture et comptes `unsupported_as_supported` par axe ; elle ne fournit ni précision/rappel par label, ni métriques par genre, ni manifeste de seuils. Conservez ces revues séparément jusqu’au besoin d’un adaptateur compatible. `release_gate` vaut toujours `unavailable`.

## Remplir une fiche par lot

Copiez cette section pour chaque tâche. Une réponse vide signifie qu’une preuve ou décision manque encore. Ces champs sont des métadonnées humaines de collecte, pas un nouveau schéma JSON d’évaluateur. Gardez approbations privées, observations originales et contenu identifiant dans l’emplacement privé approuvé ; ne commitez que des enregistrements anonymisés autorisés et des références non identifiantes.

| Question de collecte | Réponse humaine |
| --- | --- |
| Quelle tâche, quel identifiant de corpus, quelles langues et quels genres de cas couvre le lot ? | |
| Qui possède les données, et quelle preuve autorise cet usage précis et son périmètre de partage ? | |
| Où sont les octets anonymisés, leur SHA-256 et la référence privée d’autorisation ? | |
| Qui fournit les labels indépendants, qui les relit et où la preuve de leur participation réelle est-elle conservée ? | |
| Où sont les labels originaux, désaccords, décisions finales et motifs ? | |
| Quelle taxonomie/règles ont été approuvées, par qui et sous quelle référence ? | |
| Où est la carte revue des familles et splits, avec sites/événements/requêtes/pages/documents/révisions liés ? | |
| Quel support est nécessaire par tâche, label, langue et genre pertinent, et combien est collecté par split ? | |
| Quelles métriques, minimums de support, politiques d’abstention/couverture et règles d’échec ont été approuvés avant réglage ? | |
| Où est l’approbation liant les octets exacts d’entrées, labels, carte des splits et cibles à une décision humaine réelle ? | |
| Qui peut accéder aux labels held-out et quelle entrée sans labels reçoit chaque auteur de prédictions ? | |
| Quels identifiants/configurations de référence par règles et candidat optionnel utiliseront la même entrée figée et le même split ? | |

Environ 200 requêtes FR/EN est la cible initiale de #6. Ce n’est ni un minimum pour toute tâche ni une preuve de support suffisant par classe. Ne remplissez pas la fiche avec labels générés, accord entre modèles, consentement inventé ou seuils de démonstration. Pour les exercices d’implémentation, utilisez un corpus séparé déclaré `synthetic` ; ses résultats restent inéligibles à la publication.

## Figer, exécuter et revoir

1. Collectez des cas anonymisés autorisés avec références source originales. Pour les paquets de rapport, conservez versions outils/requêtes, site/propriété effectifs, dates demandées/observées, preuves de fuseau, périmètre de collecte et états manquants/erreurs. Les observations manquantes restent manquantes ; une revue humaine ne fabrique pas une vérité causale.
2. Faites annoter les labels et résoudre les désaccords par un annotateur et un autre relecteur humain avec la taxonomie approuvée. Gardez l’incertitude : `unclassified` ou `unresolved` si les preuves sont insuffisantes. Des chaînes distinctes ne prouvent pas de vrais humains indépendants.
3. Revoyez les familles et gardez chacune dans une partition avant réglage. Les membres des paires restent dans leur split. Les validateurs détectent le recoupement déclaré ; ils ne découvrent pas une paraphrase, traduction ou événement lié affecté à une autre famille.
4. Figez octets exacts d’entrées/labels/splits/cibles et hashes dans la revue approuvée avant réglage. Le manifeste des requêtes peut lier hash et cibles ; `approved_by` et `frozen_before_tuning` sont des déclarations, pas une approbation ou chronologie authentifiée. Gardez les labels held-out hors des entrées auteur et les preuves réelles d’accès/revue séparément.
5. Exécutez la meilleure référence par règles et tout candidat optionnel sur les mêmes entrées/split. Rapportez erreurs, support, omissions et abstentions par tâche ; séparez coûts, latences et calibration. Seule une décision humaine fondée sur les cibles figées peut régler la readiness de publication.

Le [guide du schéma et manifeste des requêtes](/fr/docs/classifier-evaluation/) fournit le contrat d’import existant. Pour évaluer les requêtes, utilisez les vrais chemins fournis :

```sh
python3 scripts/eval_classifier.py \
  --dataset /absolute/authorized-query-corpus.json \
  --predictions /absolute/independent-held-out-predictions.json \
  --manifest /absolute/reviewed-pre-tuning-manifest.json
```

Ces chemins décrivent des fichiers attendus ; aucun corpus autorisé ni manifeste n’est livré par cette fiche. Le succès du processus signifie que l’évaluateur a tourné, pas que les cibles sont atteintes. Le statut reste `pending_human_review` pour des données déclarées humaines, ou `ineligible_synthetic` pour des données synthétiques, même si les cibles numériques sont atteintes.

Pour la revue de rapports, `--prepare` produit les observations sans `claims`, jugements d’annotation ni labels :

```sh
python3 scripts/eval_audit_reports.py \
  --dataset /absolute/authorized-report-corpus.json --prepare --split held_out
```

Gardez ce paquet séparé du corpus annoté. L’auteur reçoit les observations ; une revue humaine indépendante identifie les affirmations du rapport candidat et conserve leurs références. L’évaluateur actuel ne consomme pas de prose et n’attache pas automatiquement des affirmations générées. Pour comparer des labels d’affirmations figés, préparez le contrat de prédiction après cette revue, puis lancez :

```sh
python3 scripts/eval_audit_reports.py \
  --dataset /absolute/authorized-report-corpus.json \
  --predictions /absolute/independent-claim-predictions.json
```

L’objet de prédictions contient exactement `corpus_id`, `split`, `reviewer` et `predictions` ; chaque ligne contient exactement `case_id`, `claim_id` et `label`. Les identifiants référencent des affirmations du split sélectionné. `reviewer` doit différer des métadonnées déclarées des auteurs d’annotation. C’est une identité déclarée, pas une preuve humaine. Les lignes manquantes réduisent la couverture et ne deviennent pas des réponses non résolues correctes. Pour évaluer un nouveau rapport, établissez d’abord des affirmations revues indépendamment et leur correspondance, plutôt que de traiter le rapport candidat comme vérité de référence.

## Preuves nécessaires pour terminer #6

Avant de revendiquer une qualité humaine, conservez fiche complétée, vraies preuves d’autorisation/revue, corpus held-out avec familles disjointes, labels réels avec historique des désaccords et cibles approuvées avant réglage. Publiez erreurs et support held-out propres à chaque tâche, y compris échecs et mesures non prises en charge. Aucun corpus humain authentique, cible numérique approuvée ou décision humaine de publication n’est fourni par cette fiche, les fixtures synthétiques ou des chaînes déclaratives d’approbation.
