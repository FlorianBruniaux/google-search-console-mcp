# C1 : évaluateurs livrés, validation humaine encore manquante

Date : 2026-10-11. Issue #6. Branche locale `codex/c1-foundation-evaluation`, base `4ac51aa53e5608d175ead22f0afb4855c9e4a491`.

## Résultat technique

Le runner de rapports expose les matrices de confusion et les mesures par axe, langue et label. Il distingue prédiction absente et label `unresolved`, et utilise `null` quand un dénominateur n’existe pas.

Un manifeste held-out lie les cibles aux octets exacts du corpus, avec contrôles de support, précision/rappel, couverture et faux supported. Les résultats sont `unavailable`, `insufficient_support`, `failed` ou `met` ; les strates non ciblées restent visibles. Les hashes des prédictions et du manifeste accompagnent le résultat. `release_gate` reste `unavailable`.

Le runner de requêtes conserve ses métriques et cibles globales ; il ajoute résultats par langue, groupe `mixed` pour paires bilingues, hash du manifeste et lecture JSON bornée. Les identités d’annotation/revue sont comparées sans casse ni espaces dans les deux runners. Ce contrôle n’authentifie personne.

Le runner d’extraction reste celui déjà livré. Ses tests ont été exécutés avec Trafilatura 2.3.1 ; le calcul est limité aux snippets, aux observations de durée et aux allocations Python. Aucune adoption par défaut ni mesure complète de qualité d’extraction n’est déduite.

## Vérifications exécutées avant revue finale

| Vérification | Résultat observé |
|---|---|
| Baseline ciblée avant changement | 170 tests réussis |
| Nouveaux tests de métriques puis implémentation | 5 échecs attendus, puis passage au vert |
| Manifeste de rapports puis implémentation | 26 échecs attendus, puis passage au vert |
| Extensions requêtes puis implémentation | 5 échecs attendus, puis passage au vert |
| Cas JSON/cibles/strates limites | 3 échecs attendus, puis corrections vérifiées |
| Trois évaluateurs | 113 tests réussis |
| Suite Python complète | 2 121 tests réussis, aucun skip rapporté |
| Sources du portail | 6 tests réussis |
| Traductions | 52 pages préparées, hashes EN/FR vérifiés |

Commandes de validation : `.venv/bin/python -m pytest -q`, `node --test tests/doc-content-source.test.mjs` et `node scripts/prepare-doc-content.mjs --verify-translations`.

L’exemple `tests/fixtures/audit_evaluation/report_*.synthetic.json` se rejoue réellement : deux claims, cibles numériques atteintes, `declarations_authenticated: false`, `synthetic_release_eligible: false` et gate indisponible. Il ne mesure pas la qualité sur des cas humains.

## Pièces humaines requises

Le [protocole C1](seo-foundation-evaluation-protocol.md) précise H1 à H10. Aucun lot authentifié, cible métier approuvée ou décision humaine de qualité n’a été fourni pour cette exécution. Des données privées non communiquées peuvent exister ; elles n’ont pas été recherchées.

| Pièces | Livrable humain attendu |
|---|---|
| H1 | Registre propriétaire/autorisation/anonymisation/rétention et hashes exacts des sources |
| H2/H3 | Vraies requêtes FR/EN annotées et paires jugées indépendamment, avec taxonomie/familles/splits |
| H4 | Trois lots de paquets source et rapports : fidélité, trafic, concurrence nuisible ; claims, pointers, labels et revue des faits omis |
| H5 | HTML FR/EN de cinq types de pages, hashes, snippets inclusion/omission et contexte d’acquisition |
| H6 | Participation réelle d’annotateur/relecteur, labels originaux, désaccords et arbitrages ; rôle d’évaluation distinct des auteurs de labels |
| H7/H8 | Familles disjointes, accès held-out contrôlé, cibles et minimums de support fixés avant réglage, preuves de chronologie/revue |
| H9/H10 | Prédictions/versions réellement évaluées, résultats held-out et décision humaine liée aux hashes par tâche |

Environ 200 requêtes est une cible de collecte initiale, pas la preuve d’un support suffisant. La taille requise pour les autres tâches et chaque strate dépend de minimums humains approuvés, actuellement absents. L’axe page/genre reste dans un registre de revue ; il n’est pas ajouté artificiellement au schéma v1.

## Limites de livraison

C1 complète la mécanique de validation et la collecte. Il laisse #6 ouverte pour les données et décisions humaines. Il ne valide pas les 96 outils, une cause de baisse de trafic, une fusion de pages, la complétude de rapports libres ou une probabilité de citation.

Aucune collecte Google, DataForSEO, modèle payant, publication produit ou déploiement n’a été effectuée. Les tests locaux et la revue de cette branche ne sont pas une validation CI/production.

Skills used: flow-lean, superpowers:executing-plans, superpowers:test-driven-development, superpowers:verification-before-completion, superpowers:using-git-worktrees, superpowers:systematic-debugging, superpowers:requesting-code-review

