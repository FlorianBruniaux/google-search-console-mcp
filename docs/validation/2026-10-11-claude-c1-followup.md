# Suivi du défaut Claude C1

Essais commencés le 10 octobre 2026, bilan consolidé le 11 octobre. Les huit cellules retenues passent les critères C1 figés : quatre cas dans Claude et Codex. Ce verdict porte sur les clics indisponibles, leur réemploi diagnostique et le contrôle positif ; il ne qualifie pas les rapports entiers d'exacts. La qualité humaine reste `UNKNOWN`.

Ce suivi prolonge les [essais clients précédents](2026-10-10-interactive-playbook-trials.md) de [#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39). #81 est fusionnée sur `main` au commit `0021bb490e685e34ead4c25d1cf66b33a577d46e`. Sa CI a réussi sur le commit source `a621a4f908aaf96e9943d9e9fb29048edcb1f618` ; le site public a ensuite servi le SHA du merge et le run de déploiement `38088641614`.

Le correctif décrit ici est intégré par [#82](https://github.com/FlorianBruniaux/google-search-console-mcp/pull/82), fusionnée sur `main` au commit `338f5a1947cdebff01f68b4de54631e63d75f404`. Sa [CI manuelle](https://github.com/FlorianBruniaux/google-search-console-mcp/actions/runs/38090426423) a réussi sur le commit source exact `144f7b49566d2ba9debaab06a048aa8c05ae06d9` : 2 081 tests Python, distributions et roue installée vérifiées, 97 tests navigateur en CI. Cette fusion n’établit pas à elle seule le déploiement public de ces changements.

## Défaut et périmètre réel

Le scénario C1 initial conservait un CTR numérique malgré des clics manquants. Lors de la reprise antérieure, Claude en tirait un compte implicite, puis le réutilisait dans son diagnostic ; il attribuait aussi une contribution à un écart global non établi. La première réponse avait surinterprété le délai de date configuré, sans reconstruire les clics. Les sorties et verdicts antérieurs restent conservés.

Cette forme est adversariale. Le producteur actuel [calcule le CTR depuis les comptes](../../src/gsc_mcp/tools/search_breakdown.py) : des clics manquants rendent aussi le CTR indisponible. Son état agrégé `availability` est une chaîne, contrairement au dictionnaire synthétique de C1. Ce scénario démontre une faiblesse de lecture face à un payload déclaré incohérent, pas une émission observée de Google ni un défaut prouvé du producteur.

Les trois nouveaux cas exécutent le vrai producteur avec des réponses fournisseur simulées. Aucun fournisseur authentifié n'est appelé. Ils conservent des comptes manquants cohérents avec un CTR nul, un agrégat initial vide, une sonde de dates indisponible et une comparaison complète servant de contre-exemple positif.

## Correction du playbook partagé

Une étape précède désormais le classement des hypothèses dans le `SKILL.md` canonique de `traffic-drop-diagnosis`. Si un compte requis manque ou si la comparaison de clics choisie est explicitement indisponible ou incompatible, le rapport indique que la baisse et son amplitude ne sont pas établies. Il ne reconstitue pas les clics pour les réutiliser dans les observations, hypothèses ou conclusions. La couverture et les erreurs restent des limites de preuve, sans contribution attribuée à une variation inconnue.

Les autres métriques observées gardent leur périmètre. Une référence optionnelle indisponible n'annule pas une autre comparaison valide. Les comptes complets et comparables permettent encore une soustraction explicite, même sans champ de delta nommé ; un delta retourné indisponible n'est pas remplacé silencieusement.

Cette modification concerne le playbook effectivement lu par les clients. Le validateur de rapports source-only n'est pas modifié : il vérifie forme et pointeurs, sans établir la vérité de la prose, et son parcours n'exécute pas ces outils MCP interactifs.

## Livraison, gel et comptabilité

Le protocole et les critères sémantiques ont été figés avant les essais du candidat. Les sessions sont fraîches, headless, avec chargement explicite du skill. Les modèles demandés sont `gpt-6.1-sol` et `opus`, effort `high`, dans Codex 0.159.2 et Claude Code 2.1.296. Leur identité concrète n'est pas attestée indépendamment. Le routage implicite et le dialogue humain à plusieurs tours ne sont pas évalués.

Les premiers résultats produits pour les nouveaux cas dépassaient la limite de contexte MCP de Claude. Le serveur répondait, mais le client recevait une erreur de taille et un chemin déporté hors du répertoire autorisé. Les deux baselines Claude et la reprise K7 ont été jugées `UNKNOWN` faute d'ingestion. Un appel retourné par le serveur ne prouve donc pas que le modèle a lu les observations. Les autres sorties volumineuses restent archivées et exclues de la matrice retenue.

Une seconde version de livraison prépare une projection déclarée, sans changer les comptes, arguments ou critères. Elle retire seulement les enveloppes explicatives répétées aux chemins `/_meta/evidence`, `/weekday_reference/upstream_meta/evidence` et `/report_contract`. Les résultats complets sont conservés séparément ; les champs retenus sont comparés exactement à leur source. Les projections font respectivement 9 443, 9 224 et 9 305 caractères/octets JSON. Le nombre de tokens propre aux clients reste `UNKNOWN`.

Le candidat n'a pas changé après son gel. Le cas M4 était réservé avant ce gel ; il reste un cas d'auteur, sans annotation humaine indépendante. Les clients ne reçoivent pas l'oracle opérateur. Les identifiants affichés sont opaques.

Deux configurations immuables comptent dix puis huit tentatives natives, sans augmenter le premier plafond. Les dix-huit lancements retournent dix-huit rapports techniques. Les traces conservent vingt-six tentatives MCP : vingt et une réponses déclarées et cinq refus. La matrice retenue utilise huit appels retournés. Une tentative native ne constitue pas un plafond de coût ou de tokens.

Le serveur expose les signatures réelles, canonise les paramètres et leurs defaults, refuse les autres requêtes et n'appelle jamais les implémentations fournisseur. Chaque session a un plafond effectif de deux appels de replay, même lorsque le manifeste original en déclare douze. Les processus sont bornés à 180 secondes, avec deux sessions simultanées par lot et les limites de sorties existantes. Les ledgers ne mesurent pas les appels MCP du replay ; leurs compteurs fournisseur ne sont pas, seuls, une preuve d'absence d'acquisition.

## Verdicts retenus

| Cas | Provenance de la réponse | Claude | Codex |
| --- | --- | --- | --- |
| C1, compte manquant avec CTR incohérent | Payload adversarial original | PASS pour C1 | PASS pour C1 |
| K7, clics comparés et CTR manquants | Producteur simulé, projection déclarée | PASS pour C1 | PASS pour C1 |
| M4, agrégat initial vide et sonde indisponible | Producteur simulé, projection déclarée | PASS pour C1 | PASS pour C1 |
| P2, comptes observés comparables | Producteur simulé, projection déclarée | PASS pour C1 | PASS pour C1 |

La revue Astra distincte examine les dépendances des affirmations, leur modalité et les sources, sans liste de mots interdits. Les huit sessions retenues ont lu le skill corrigé intégralement. Le contenu MCP décodé dans les événements natifs est identique au fixture retenu, avec comptes, deltas, fenêtres, compatibilité et référence présents. Une vérification exécutée par l'agent principal confirme ces égalités, les hashes, les appels exacts et les plafonds.

Le cas positif conserve la baisse arithmétique attendue, sans refus général de calculer. Les nouvelles baselines Claude lisibles donnent P2 `PASS` et K7 `UNKNOWN` : certaines hypothèses de K7 sont ambiguës malgré la conservation des comptes manquants. Elles ne sont pas transformées rétroactivement en un échec reproduit du producteur. La régression avant/après confirmée reste le C1 adversarial précédemment échoué.

## Limites et suite de #39

Des propositions de prochains contrôles restent trop affirmatives : davantage de budget ou une fenêtre plus ancienne ne garantit pas la complétude future ; les vues page et requête séparées ne prouvent pas un croisement. Une association implicite entre pages et requêtes a aussi été relevée. Ces écarts sont conservés pour la revue de qualité, sans annuler le verdict spécifique C1 ni déclarer les rapports entièrement exacts.

#39 reste ouverte : compléter les erreurs/reprises MCP réelles et la dimension Bing `device`, puis appliquer les [annotations humaines indépendantes de #6](../expert-evaluation-intake.md). Le périmètre HTML/CrUX reste à décider avant extension. Aucune nouvelle acquisition réelle, écriture sur un site, publication de données privées ou release PyPI n'est réalisée par ce lot.

La suite Python locale complète passe avec 2 081 tests ; la vérification du site passe avec 113 tests navigateur. Les tests de contrats vérifient les projections des deux clients. La calibration BM25 locale sur les 252 scénarios d'auteur reste admissible pour les quinze cibles ; trafic : F1 0,94, précision 0,89, rappel 1, un faux positif. Aucun hook ou index global n'a été modifié ; le routage global effectif reste non vérifié.

## Hashes conservés

| Artefact | SHA-256 |
| --- | --- |
| Ancien skill, après #81 | `fbbb22be3ea2f2c56170c6587c9c4c5106d54ca6e78c4478e96bee5543911485` |
| Candidat figé et testé | `e98507621c1e38e270fad9799af7adbf4e1f15cdbb030ea093688c88e09a2997` |
| Manifeste initial du protocole et des fixtures | `4f40d6f3611e0785fbbbe14a77a43e75bf51ac336d903bc96e858113882ef3c6` |
| Manifeste de livraison v2 | `ba3d60165395cd49529749bd89130688a44b68a9bbd537608fc60689a2e211f7` |

Les fichiers privés, événements originaux, refus et baselines sont conservés hors du dépôt. Les hashes identifient leurs bytes ; ils ne prouvent ni vérité sémantique ni approbation humaine.
