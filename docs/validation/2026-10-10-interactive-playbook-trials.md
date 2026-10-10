# Essais des playbooks dans les clients natifs, 2026-10-10

Date : 2026-10-10. Statut : douze réponses initiales et quatre reprises ciblées avec lecture du skill et appels MCP observés, plus deux reviewers frais. La matrice retenue après reprises donne onze cellules conformes sur douze dans leur périmètre contrôlé ; C1-Claude conserve un écart. Le retour technique ne constitue pas un verdict sémantique global. La qualité humaine reste `UNKNOWN`.

Cette note complète le [pilote GSC authentifié](2026-10-10-live-gsc-readiness.md) pour [#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39). Le pilote précédent a acquis des observations fournisseur et les a confiées à des lecteurs source-only. Ces essais chargent les playbooks dans les clients natifs et leur font appeler un serveur MCP de replay déclaré. Les observations contrôlées ne deviennent pas de nouvelles mesures Google ou Bing.

Le [suivi C1](2026-10-11-claude-c1-followup.md) ajoute une branche explicite pour les comptes indisponibles et des essais distincts. Il précise une limite de ce scénario d'origine : le CTR numérique conservé malgré les clics manquants, ainsi que la forme de son champ `availability`, ne sortent pas du producteur actuel. C1 reste un payload adversarial déclaré ; l'échec observé ici ne démontre pas que Google ou le producteur réel émet cette combinaison. Le bilan historique ci-dessous conserve ses sorties et verdicts.

## Périmètre des douze réponses initiales

Les clients sont Codex `0.159.2` et Claude `2.1.296`, versions relevées par l'opérateur. Les modèles demandés sont `gpt-6.1-sol` et `opus`, avec effort `high`. Les reçus consignent la demande de modèle ; cette note n'établit pas son identité par une mesure indépendante. La référence source enregistrée pour le bilan initial est `d6fd3ddc6d19cc84ddde15a7bfaa1a6c35bed3e7`.

Chaque session reçoit une copie intégrale du `SKILL.md` canonique correspondant, dans un répertoire local propre au client, et une demande explicite de l'appliquer. Les cas d'évaluation et leurs labels attendus ne sont pas copiés dans ce répertoire. Les événements natifs conservent la lecture du skill, les appels d'outils et la sortie finale ; les reçus conservent les hashes du skill et du manifeste utilisé.

Ce protocole observe une application explicite en mode headless. Il ne mesure pas le routage automatique des skills, un dialogue humain à plusieurs tours, l'utilisation générale des deux clients ou la qualité d'un audit humain.

## Frontière du replay et traces

Le manifeste de chaque scénario déclare ses outils, leurs requêtes autorisées, leurs réponses et un plafond de douze tentatives MCP. Le serveur dérive les signatures et schémas depuis le registre réel, sans appeler les implémentations enregistrées. Il canonise les arguments déclarés et reçus avec les valeurs par défaut de la signature ; une propriété différente, un argument supplémentaire ou une autre valeur est refusé. Il ne propose aucun fallback fournisseur.

Le serveur expose uniquement les outils du manifeste. Il enregistre l'inventaire au démarrage et dans le callback de découverte, puis les arguments, réponses ou refus de chaque appel. Chaque événement porte un UUID, une date UTC, le scénario, son digest et la provenance `controlled_mcp_replay_not_provider_execution`. La trace est créée exclusivement en mode `0600` ; un fichier existant, un symlink ou un parent absent est refusé. Après le plafond, les requêtes supplémentaires sont refusées et restent tracées. Les trames protocole malformées qui ne deviennent pas un appel d'outil sont hors de cette trace.

Les tests offline ont exercé une vraie connexion MCP stdio, la découverte, une réponse autorisée, un changement de propriété, un argument supplémentaire, un outil non exposé et le dépassement du plafond. L'instrumentation des fonctions du registre a constaté zéro appel à leurs implémentations. Les six tests du serveur ont passé ; cela vérifie la frontière de replay, sans exécuter les providers.

Les fichiers privés conservent les bytes originaux des manifestes, skills copiés, prompts, événements natifs, traces MCP, réponses et reçus. Cette note publie seulement leur méthode et des hashes de référence. Les données, identités de propriétés, requêtes, URL et chemins de stockage restent hors du dépôt.

## Cas et appels MCP effectivement observés

Les douze sorties initiales portent le statut technique `returned; semantic_quality_unverified`. Les traces contiennent quatorze appels de replay par client, soit vingt-huit au total. Tous ces appels ont reçu leur réponse allowlistée ; cette réussite du replay ne transforme pas une réponse fournisseur indisponible en source exploitable.

| Cas | Playbook et branche contrôlée | Outils appelés | Codex | Claude |
| --- | --- | --- | --- | --- |
| C1 | `traffic-drop-diagnosis` : couverture incomplète, agrégat de clics manquant, référence indisponible | `search_weekday_reference` | 1 | 1 |
| C2 | `cannibalization-check` : plusieurs URL pour une requête commune, dommage non démontré | `seo_cannibalization`, `get_advanced_search_analytics`, `get_search_analytics`, deux `inspect_url` | 5 | 5 |
| C3 | `indexing-audit` : résultats d'inspection dont un état unspecified, puis indisponibilité d'un autre batch | Deux `batch_url_inspection` distincts | 2 | 2 |
| C4 | `ai-overviews-impact` : preuve d'exposition IA absente malgré des lignes de recherche | `ai_overviews_impact`, `compare_search_periods` | 2 | 2 |
| C5 | `traffic-drop-diagnosis` : famille GA4 absente de la découverte, réponse Bing indisponible | `get_capabilities`, `compare_search_periods`, `bing_query_stats` | 3 | 3 |
| C6 | `traffic-drop-diagnosis` : dimension non prise en charge pour la comparaison Bing | `compare_search_engines` | 1 | 1 |

C3 conserve deux réponses de batch séparées. Il ne simule pas un batch réel qui mêlerait une erreur globale et des résultats acquis. Dans C5, l'inventaire annoncé correspond aux outils exposés ; la famille GA4 est absente de la découverte. Dans C6, le serveur retourne le payload d'erreur contrôlé dans une enveloppe MCP réussie. Ce cas éprouve la lecture d'une erreur source dans le contenu, pas une exception de transport MCP ni l'exécution du refus par l'implémentation Bing.

## Tentatives vides et comptabilité native

Deux tentatives Codex ont précédé la réponse C1 exploitable et n'ont produit aucune preuve d'exécution du playbook via MCP. La première avait été déclarée `returned` parce que le lanceur acceptait un code de sortie zéro sans vérifier les événements et le rapport final. Une correction opérateur conservée séparément annule ce statut de réussite ; le reçu original reste retenu. La seconde tentative est `unavailable`. Ces deux tentatives comptent dans le budget, mais ne comptent ni comme réponses exploitables ni comme passes.

Le premier ledger conserve son plafond de dix-huit tentatives natives : douze réponses initiales, deux tentatives vides, deux reviewers frais et deux reprises C1. Un défaut distinct C4 a motivé une seconde configuration immuable, limitée à deux tentatives, pour retester uniquement ce cas dans les deux clients. Le premier plafond n'a pas été modifié. Total : vingt tentatives de lancement, dix-huit sorties reçues dont seize rapports de playbook et deux reviews. Les réservations ne sont ni des mesures de coût ni des preuves de qualité.

Le lanceur borne chaque processus à 180 secondes et limite la concurrence à deux sessions. Son ledger compte les tentatives natives ; les appels MCP sont comptés séparément dans les traces du replay. Le bilan initial compte vingt-huit appels servis ; les reprises C1 en ajoutent deux et les reprises C4 quatre, soit trente-quatre réponses allowlistées, sans refus du harness pendant ces sessions. Une réponse allowlistée peut contenir une indisponibilité métier. Les compteurs fournisseur et outil du ledger de comptabilité native restent à zéro : le replay n'utilise pas ces méthodes d'acquisition, et ces compteurs ne mesurent pas ses appels MCP.

## Constats et reprises ciblées

La réponse initiale Claude préserve l'agrégat de clics manquant et la couverture non comparable, mais présente `report_lag_days` comme un retard de publication GSC. Elle place ensuite en tête une hypothèse selon laquelle ce retard contribue déjà au signal apparent. Les sources contrôlées établissent une règle de sélection des dates et une couverture insuffisante ; elles ne mesurent pas un retard réel de publication ni sa contribution causale. Le label « hypothèse » et une confiance qualifiée ne fournissent pas cette preuve manquante.

La correction du playbook `traffic-drop-diagnosis` précise que le cutoff et `report_lag_days` décrivent une règle de requête. Elle maintient le retard de publication et les incidents de collecte à `UNKNOWN` sans observation indépendante. Elle distingue aussi le manque de couverture de son explication. Cette modification est un correctif d'instruction, pas une preuve que le comportement des clients a changé.

Les deux reprises C1 ont lu le skill corrigé et appelé l'outil avec les mêmes paramètres et réponses. Codex reste conforme au cas contrôlé. Claude distingue désormais la règle de date du retard réellement observé, mais attribue encore une contribution à la couverture inégale alors que clics et delta restent `null`. Il calcule aussi un proxy depuis CTR et impressions, puis le réemploie dans une hypothèse. Ce progrès partiel ne rend pas le retest Claude conforme. Les réponses originales et les échecs restent conservés.

La réponse initiale C4-Claude transforme un ratio arithmétique en part des impressions de la période comparée, malgré `observed_window=null` pour la ligne d'apparence et une compatibilité de données non établie. Elle rejette correctement la causalité IA ; ce rejet n'annule pas le défaut de périmètre du ratio. Le correctif `ai-overviews-impact` exige des fenêtres source, couvertures observées, surfaces de recherche et états de données compatibles avant d'annoncer une part de période. Il autorise encore une arithmétique explicitement séparée, sans interprétation de part de période ou de part IA. Les deux reprises C4 ont retourné un rapport avec le même manifeste ; leur verdict sémantique est consigné ci-dessous après revue distincte.

## Revue distincte des sorties

Une revue Astra distincte vérifie les douze lectures de skills, les hashes des manifestes et les vingt-huit requêtes/réponses initiales contre les fixtures. Elle donne les verdicts initiaux suivants. `PASS_WITHIN_FIXTURE_SCOPE` ne vaut que pour ces paramètres, réponses et questions ; `FAIL` désigne une suraffirmation localisée dans la sortie.

| Scénario initial | Codex | Claude |
| --- | --- | --- |
| C1, couverture et agrégat manquants | PASS_WITHIN_FIXTURE_SCOPE | FAIL, attribution de publication non soutenue |
| C2, chevauchement multi-URL | PASS_WITHIN_FIXTURE_SCOPE | PASS_WITHIN_FIXTURE_SCOPE |
| C3, indexation inconnue | PASS_WITHIN_FIXTURE_SCOPE | PASS_WITHIN_FIXTURE_SCOPE |
| C4, preuves IA absentes | PASS_WITHIN_FIXTURE_SCOPE | FAIL, part de période non soutenue |
| C5, branches indisponibles | PASS_WITHIN_FIXTURE_SCOPE | PASS_WITHIN_FIXTURE_SCOPE |
| C6, refus décrit pour `country` | PASS_WITHIN_FIXTURE_SCOPE | PASS_WITHIN_FIXTURE_SCOPE |

Le retest C1 donne `PASS_WITHIN_FIXTURE_SCOPE` pour Codex et `FAIL` pour Claude. Le retest C4 donne `PASS_WITHIN_FIXTURE_SCOPE` pour les deux clients : la part de période reste indisponible, et le ratio arithmétique éventuel est séparé avec ses scopes non résolus. La matrice retenue remplace uniquement C1/C4 par leurs reprises : onze cellules conformes sur douze, avec vingt-huit appels MCP associés. Les sorties initiales et les trente-quatre appels de toutes les sessions restent conservés. Ces reprises ajustent les instructions après observation du même cas : elles ne sont pas des essais hors échantillon.

Deux reviewers frais examinent un jeu synthétique de cinq claims, sans labels opérateur dans leur contexte. Chacun retourne cinq labels exacts sur cinq : trois affirmations non soutenues de pénalité, causalité IA et fusion sont rejetées ; une différence arithmétique est soutenue ; une contribution explicitement hypothétique reste non résolue. Aucun des trois claims non soutenus n'est promu en fait. Les quinze références Codex et dix-sept références Claude se résolvent dans les sources fournies ; la revue distincte confirme les justifications. Ces résultats sur cinq fixtures ne fournissent pas des annotations humaines indépendantes ni un seuil de qualité pour #6/#39.

Les deux skills modifiés conservent description, paramètres et corpus de routage. Les quarante tests des contrats/projections passent. La calibration BM25 locale de chaque client utilise 252 scénarios d'auteur sur quinze cibles ; toutes restent admissibles au seuil du script. Le trafic a F1 0,94, précision 0,89, rappel 1 et un faux positif ; le skill IA a F1 0,73, précision 0,57, rappel 1 et six faux positifs. Ces valeurs ne sont pas des mesures hors échantillon. Aucun index ou hook global n'a été modifié ; le routage global effectif reste non vérifié.

Priorités restantes de #39 : traiter la suraffirmation C1-Claude sans promouvoir une métrique indisponible, conserver des cas indépendants via #6, compléter les pannes/reprises et le véritable statut d'erreur MCP, puis examiner la dimension `device` non exécutée ici. Le routage implicite et le dialogue humain multi-tour restent hors des preuves de ce lot. Le [protocole expert](../expert-evaluation-intake.md) demeure nécessaire pour les annotations et décisions humaines.

Les contrôles locaux du lot passent : quarante tests de contrats/projections, six tests du serveur privé de replay et la vérification complète du site, dont 113 tests navigateur. La suite Python complète du pilote précédent n'a pas été relancée pour ce lot de skills et de documentation.

## Hashes de référence du bilan initial

| Artefact conservé | SHA-256 |
| --- | --- |
| Serveur MCP de replay | `6a2882524716beceb2b434254ba216b275d7e0556a4c3c5d9a66406e325e589d` |
| Tests offline du serveur | `b42482aad64ffcab07c96dee2676f5b5b311a40c6f75a701e472451863e76dad` |
| Skill `traffic-drop-diagnosis` du bilan initial | `2ba44f39eeb50a686022ba1322a7a4018398c78d744ad35ed7a4e26c844c3a2a` |
| Skill `traffic-drop-diagnosis` corrigé, avant reprises | `fbbb22be3ea2f2c56170c6587c9c4c5106d54ca6e78c4478e96bee5543911485` |
| Skill `ai-overviews-impact` corrigé, avant reprises | `c00cc1c96d294c21a980d9e6decfd52301b460672de54f38a53c8b17c9ab85cb` |
| Manifeste C1 commun aux deux clients | `31ab8386fcbbfaeebce48702f901d416ea9d9e5cb54dad15171e47e80f573b02` |
| Réponse initiale C1-Claude | `348bba83e5d4f34ca555c2278e4860e1f0b630321bab9079a3fcfd618a8c4526` |
| Réponse initiale C1-Codex exploitable | `b0c88f59edea36632248ab716f32c97a08d818539e6c1c8238d37cb34d35baff` |
| Correction opérateur de la première tentative Codex vide | `53822990a596772e91bea87731d0b4b21fb79571d3142b550b2666238bc5e5e3` |

Les hashes identifient des bytes retenus. Ils n'attestent ni leur vérité sémantique ni une approbation humaine.
