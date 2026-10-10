# Validation GSC réelle et limites restantes de #39

Date : 2026-10-10. Statut : acquisition authentifiée et lectures natives source exécutées ; playbooks interactifs `NOT_RUN`, qualité humaine `UNKNOWN`. Référence de départ : `f5a32731778f54f73df37a82d7417a9fb4558093`, branche `codex/gsc-live-readiness`, avec les correctifs décrits ci-dessous.

Le parcours borné et ses lecteurs natifs nécessitent le checkout source et son environnement Python 3.11+. La roue PyPI `gsc-mcp-tools==1.5.0` seule ne fournit pas ces scripts. Le catalogue public par défaut reste à 96 outils. Cette note conserve le protocole initial et le bilan technique de [#39](https://github.com/FlorianBruniaux/google-search-console-mcp/issues/39), sans publier les observations privées ni fournir un corpus humain ou un verdict de qualité.

## Entrées à renseigner avant acquisition

| Entrée | Valeur attendue et preuve à conserver |
| --- | --- |
| Propriété Google | Nom ou URL du site fourni par le demandeur, puis propriété domaine ou préfixe URL exact repris comme `site`. `get_site_details(site_url=...)` vérifie cette seule propriété. Si une résolution depuis `list_properties().properties[].url` est nécessaire, déclarer séparément cette lecture de l'inventaire du compte. Conserver la permission retournée et le résultat de l'accès effectif. Une variable d'authentification déclarée ne prouve pas cet accès. |
| Objectif | Question à résoudre : indexation d'URL choisies, chute de trafic, résultats multi-URL, rapport périodique. Pour une chute, fournir la date approximative ; à défaut, l'opérateur propose des périodes fixes pour commencer. |
| Échantillon | Liste explicite des URL, taille, source et règle de sélection. Inclure des URL absentes des lignes de recherche si l'objectif le demande. Un échantillon sélectionné dans les lignes retournées ne représente pas nécessairement les meilleures pages de toute la propriété. |
| Fenêtres | Dates inclusives `baseline_start`, `baseline_end`, `comparison_start`, `comparison_end`, égales, ordonnées et disjointes pour `search_change_breakdown`. Renseigner aussi `dimensions`, `filters`, `search_type`, `data_state` et `aggregation_type`. Garder dates demandées et dates observées séparées. |
| Accès et stockage | Mode GSC existant, référence privée d'autorisation pour les données et leur partage, dossier privé absolu déjà créé hors du dépôt. Les secrets restent dans la configuration locale prévue par [Google setup](../google-setup.md), jamais dans la note ni dans les arguments d'outils. |
| Limites | Nouveau `run_id`, `ledger_path`, liste `allowed_tools`, plafonds `max_provider_attempts`, `max_tool_calls` et, si revue native, `max_native_calls`. Choisir les nombres à partir du plan réel ; aucun plafond monétaire n'en découle. |
| Fournisseurs optionnels | Google suffit pour commencer. Si Bing est demandé, renseigner son `bing_site` exact et vérifier son accès propre. Si GA4 est demandé, renseigner `ga4_property` explicitement et vérifier son accès. Autoriser leur périmètre de données séparément. |
| Revue native optionnelle | Hôte `codex` ou `claude`, modèle pris en charge par cet hôte, rôles sélectionnés et partage du paquet autorisé vers cet hôte. Un alias Claude ne devient pas un identifiant Codex. |

`get_search_analytics` accepte `site`, `days`, `dimensions`, `row_limit`, sans dates fixes. Son code sélectionne une fenêtre finissant trois jours avant la date locale d'exécution ; sa pagination interne ne conserve pas `row_limit` comme plafond des lignes retournées. Ce parcours historique ne borne donc pas le pilote par ce paramètre. Employer `search_change_breakdown` avec ses dates fixes, ou `search_weekday_reference` avec `days` et `end_date` explicites, puis contrôler probes de dates et couverture. Le décalage codé de trois jours ne mesure pas le retard réel de la propriété.

Le nom ou l'URL du site suffit au demandeur pour lancer la préparation. L'opérateur peut proposer l'objectif, l'échantillon et les fenêtres à partir de ce site, puis retenir leur périmètre explicite avant acquisition. La liste ci-dessus décrit le dossier de run complet, sans exiger que le demandeur compose lui-même une configuration technique.

Le correctif de cette branche rend `bing_site` facultatif pour un plan Google seul. Une URL Bing explicite et valide reste obligatoire dès qu'un outil Bing ou `compare_search_engines` est autorisé. Les configurations existantes qui fournissent ce champ conservent leur identité ; le retirer d'un run déjà enregistré nécessite un nouvel ID.

## Parcours d'exécution existant

1. **Figer le périmètre.** Inventorier le checkout, l'environnement Python et les versions des clients. Faire confirmer la propriété et le partage autorisé, puis sélectionner les outils en lecture seule. Utiliser `get_capabilities` pour connaître la surface découverte, `get_site_details` pour vérifier la propriété sélectionnée. Exclure `list_properties` du plan monopropriété, car il retourne l'inventaire du compte. Si une lecture d'inventaire est nécessaire et autorisée, la distinguer du pilote ; tout appel hors session bornée reste hors compteurs du runner.
2. **Préparer les fichiers privés.** Garder configuration, requêtes, ledger SQLite, observations, rapports et manifestes de hashes dans le dossier autorisé hors dépôt. Un chemin tel que `/absolute/private-gsc-run/` est un exemple à remplacer, pas un dossier fourni. Vérifier avant acquisition que le parent de sortie existe, est privé et accessible en écriture, et que la sortie n'existe pas. Le ledger doit avoir un parent existant, un chemin absolu et ne pas être un lien symbolique. Les requêtes sont un tableau JSON de `{ "tool": ..., "arguments": ... }` ; copier les contrats du [guide du runner](../bounded-native-audit.md#prepare-an-explicit-run), puis remplacer chaque propriété, URL et chemin d'exemple.
3. **Acquérir sous budget.** Lancer le runner source sur ce plan validé. Il vérifie toutes les requêtes avant acquisition, acquiert séquentiellement et conserve une branche `unavailable` pour une source refusée, échouée ou hors budget. Inspecter le JSON final avant toute interprétation ; une sortie créée ou un code de retour réussi ne prouve pas la réussite du fournisseur. `batch_url_inspection` accepte au plus 10 URL ; chaque URL peut consommer une tentative fournisseur, et les reprises peuvent en consommer davantage.
4. **Revoir les observations.** Avec un hôte et un modèle choisis explicitement, le même runner acquiert d'abord, puis distribue le paquet aux rôles source-only, à l'auteur et à une invocation fraîche du reviewer. Sans hôte, il acquiert seulement. Prévoir les réservations des rôles plus auteur/reviewer dans `max_native_calls`. Les rôles ne chargent pas les playbooks interactifs et n'ajoutent pas de requêtes. Les lecteurs reçoivent le paquet complet ; leur périmètre de références n'est pas un filtre de confidentialité.
5. **Essayer les playbooks par client.** Exécuter les scénarios ci-dessous dans des sessions distinctes de Codex et Claude, avec leurs projections de `.agents/skills/`. Conserver les outils effectivement appelés, paramètres, réponses et refus pour chaque client. La réussite du runner source ne valide ni le routage interactif ni le comportement d'un playbook.

Commande d'acquisition seule, avec chemins d'exemple à remplacer :

```sh
GSC_NO_BROWSER=1 python scripts/run_bounded_audit.py \
  --config /absolute/private-gsc-run/config.json \
  --requests /absolute/private-gsc-run/requests.json \
  --output /absolute/private-gsc-run/acquisition.json
```

Pour un run natif explicitement choisi, ajouter `--host codex --model gpt-6.1-sol`, ou `--host claude --model <modele-pris-en-charge-par-Claude>`, et les options de rôles du [guide natif](../bounded-native-audit.md#optional-source-only-specialists). Il s'agit d'instructions, aucun de ces appels n'est exécuté par cette note.

La CLI actuelle ne prend pas un paquet d'acquisition sauvegardé comme entrée de revue. Une relance réacquiert les sources ; son cache est limité à la session. Réutiliser un `run_id` poursuit les compteurs persistants et interdit de modifier sa configuration. Un nouveau périmètre nécessite un nouvel ID. Choisir un nouveau fichier de sortie, le runner refuse d'écraser un fichier existant. Pour comparer Codex et Claude, enregistrer chaque run séparément et comparer les hashes et fenêtres des observations ; ne pas présumer des entrées identiques après deux acquisitions.

`GSC_NO_BROWSER=1` rend explicite l'absence de connexion OAuth interactive pendant le run ; préparer l'authentification séparément si elle manque. Les processus natifs héritent de l'environnement local. Le sandbox Codex autorise des commandes en lecture seule : ce parcours ne prouve pas une isolation totale des fichiers, de l'environnement ou des secrets.

## Scénarios à documenter pour #39

Chaque scénario conserve son client, sa propriété, ses sources, ses paramètres, son résultat et sa limite. Les essais interactifs restent `NOT_RUN` ; le pilote source décrit plus bas observe une couverture datée incomplète et un épuisement réel du budget. Une variante synthétique doit être nommée comme telle et conservée séparément des observations authentifiées.

| Cas | Résultat à vérifier |
| --- | --- |
| Retard ou chute de trafic | Dates retournées, probes, couverture, lignes manquantes, zéro observé et références historiques restent distincts. Les causes proposées restent des hypothèses. Aucun signal de concentration ou anomalie ne devient une pénalité Google. |
| Résultats multi-URL légitimes | Le chevauchement query/page ne justifie pas une fusion, une redirection ou une canonical sans examen de l'intention et du dommage. Conserver les inspections et les lignes de chaque URL séparément. |
| Indexation inconnue ou contradictoire | Préserver verdict, couverture, fetch, robots, état d'indexation, canonicals et dernier crawl. `PAGE_FETCH_STATE_UNSPECIFIED`, inspection absente et erreur API ne deviennent pas un verdict non indexé. La catégorie locale doit être relue contre les champs source. Ne pas extrapoler à toute la propriété. |
| Preuves IA absentes | Des lignes `searchAppearance` génériques ne prouvent ni exposition AI Overviews, ni absence d'IA, ni perte causale de clics. La branche sans preuve reste indisponible. |
| Fournisseur, famille ou budget indisponible | Rapport partiel, compteurs et raison du refus restent visibles ; les branches valides restent conservées. L'absence de résultat n'est pas un zéro de trafic. Vérifier le refus avant dispatch hors plafond sans prétendre que le plafond mesure le coût. |
| Dimensions Bing non prises en charge | Conserver le refus ou la limite de capacité avec l'identité Bing. Comparer seulement des fenêtres et métriques réellement compatibles ; `bing_url_info` ne remplace pas Google URL Inspection. |
| Affirmation non soutenue | Examiner les claims de pénalité, causalité IA et consolidation contre les pointeurs source. Une référence syntaxiquement valide ou l'accord auteur/reviewer ne prouve pas le sens de l'affirmation. |

L'acquisition HTML/CrUX complémentaire reste hors allowlist du runner actuel. Le spécialiste schema reste indisponible sans source adaptée. Avant une recommandation de modification du site, obtenir les réponses publiques pertinentes (HTTP, robots, canonical) par un parcours autorisé séparé et en conserver les limites ; ne pas inventer ces observations pour remplir le rapport.

## Preuves et critères de compte rendu

Conserver les bytes originaux et leur SHA-256, le SHA du code, la configuration et les requêtes figées, l'heure de collecte avec timezone, l'identité effective du fournisseur/propriété, les fenêtres demandées et observées et les raisons d'indisponibilité. Garder `_meta.sources` et `_meta.evidence.fields` près des conclusions : `measured/observed`, `derived/calculated`, `rule/heuristic`, `null/unavailable` décrivent la méthode, sans probabilité ni permission d'écriture.

Compter les URL demandées, effectivement inspectées et sans réponse ; les observations reçues, échouées et omises ; les claims soutenus, non soutenus et non résolus. Nommer le dénominateur et le périmètre de chaque chiffre. Les champs natifs de run sont `provider_attempts`, `tool_calls`, `native_attempts`. Ils comptent des réservations/tentatives, pas des succès. Les credentials résolus et les fetches auxiliaires sont hors contrat ; `tool_calls` inclut les réutilisations du cache. Les compteurs cumulés doivent être distingués des différences avant/après un run.

Un champ absent, `null`, `UNKNOWN`, `unavailable`, une ligne non retournée ou une inspection échouée n'est pas un zéro mesuré. Même si un champ ancien contient zéro, conserver sa métadonnée d'indisponibilité. Les vues page/query/device/country décrivent le même trafic sous des axes alternatifs ; ne pas additionner leurs contributions. Une fenêtre demandée égale n'établit pas une couverture ou une timezone égale.

La validation structurelle du rapport vérifie les formes et les références, pas leur soutien sémantique. Pour un verdict de qualité #39, recueillir des claims revus par des humains indépendants et des cibles gelées via [l'intake expert](../expert-evaluation-intake.md). `scripts/eval_audit_reports.py`, piste `report_fidelity`, compare les labels de claims fournis ; il ne mesure pas l'exécution native, les omissions de preuve ou les rapports en prose. Son `release_gate` reste `unavailable`. Une acquisition réelle peut commencer sans corpus ; elle ne clôture pas la validation de qualité.

## Checklist initiale de préparation

`READY` signifie que l'entrée ou le contrôle nommé a sa preuve au périmètre indiqué. `UNKNOWN` signifie que la preuve manque ou ne permet pas de conclure. `NOT_RUN` signifie que l'exécution nommée n'a pas eu lieu. Ces statuts de suivi ne sont pas des valeurs ajoutées à l'API.

| Contrôle | État de cette préparation | Passage à READY |
| --- | --- | --- |
| Contrats du runner, fenêtres et inspection relus | READY | Références locales ci-dessous, aucune API appelée. |
| Propriété, permission et accès GSC effectif | UNKNOWN | Propriété sélectionnée et réponse authentifiée conservée. |
| Objectif, URL et fenêtres autorisés | UNKNOWN | Liste et sélection figées dans les fichiers privés. |
| Stockage privé, partage et budgets du run | UNKNOWN | Chemins existants et périmètre autorisé documentés. |
| Accès Bing/GA4 si demandé | UNKNOWN | Fournisseur demandé et preuve d'accès effective, ou exclusion déclarée du périmètre. |
| Acquisition authentifiée bornée | NOT_RUN | Paquet, traces, hashes et compteurs relus, échecs explicites. |
| Revue native source Codex et Claude | NOT_RUN | Preuves distinctes par hôte avec modèle, branches et compteurs. |
| Playbooks interactifs Codex et Claude | NOT_RUN | Preuves par client et scénario, sans substitution par un run source. |
| Qualité humaine #6/#39 | UNKNOWN | Cas autorisés, labels indépendants, cibles gelées et décision humaine réelle. |

## Références vérifiées localement

- [Runner source](../../scripts/run_bounded_audit.py) : format des entrées, acquisition avant revue, erreurs conservées, sortie privée exclusive.
- [Session bornée](../../src/gsc_mcp/audit_runtime.py) : allowlist, scope, configuration, ledger, cache et compteurs durables.
- [Propriétés](../../src/gsc_mcp/tools/properties.py), [analytics](../../src/gsc_mcp/tools/analytics.py), [comparaison datée](../../src/gsc_mcp/tools/search_breakdown.py), [inspection](../../src/gsc_mcp/tools/inspection.py) : identités, signatures, fenêtres et limite de batch.
- [Revue native](../../src/gsc_mcp/native_audit.py), [rôles source](../../src/gsc_mcp/native_roles.py), [playbook indexing-audit](../../.agents/skills/indexing-audit/SKILL.md) : sources, invocations séparées et limites d'interprétation.
- [Plan de travail, A2](../remaining-work-action-plan-2026-10-10.md#a2-valider-le-parcours-réel-et-les-playbooks-interactifs-p1), [playbooks partagés](2026-10-09-shared-playbooks.md), [guide borné](../bounded-native-audit.md) : scénarios #39, distinction source/interactif et cadre source-only/PyPI.

Les contrôles initiaux ci-dessus portaient sur les liens locaux, les noms/signatures du code et la relecture documentaire. Le bilan suivant consigne les exécutions réalisées après sélection du site par le demandeur. Les résultats historiques des autres notes ne deviennent pas des résultats de ce pilote.

## Bilan technique du pilote exécuté

L'utilisateur a choisi un sous-domaine précis. La découverte de propriété, séparée du ledger, a résolu sa propriété domaine et le contrôle authentifié a retourné `siteOwner`. Le domaine parent a été exclu. Le pilote Google seul utilise cinq URL sélectionnées dans la navigation publique, deux fenêtres demandées de 28 jours, quatre outils de lecture et des fichiers privés hors dépôt. Les données de propriété, URL, trafic et rapports bruts ne sont pas publiées ici.

L'acquisition a exécuté le script source avec un module installé depuis une roue corrective locale `1.5.0`. Cette roue n'est pas une publication PyPI. Elle inclut la configuration Google seule, l'absence de connexion OAuth interactive et les catégories d'inspection corrigées. Le code natif utilisé précède le correctif de références temporaires découvert pendant la revue ; cette distinction est conservée dans le manifest privé.

| Exécution | Résultat observé |
| --- | --- |
| Contrôle d'accès et première acquisition | 20 tentatives fournisseur, 9 appels d'outils cumulés. Plafond atteint avant 2 inspections, branches explicitement indisponibles. Le contrôle d'accès fait partie des 9 appels mais a son propre paquet. |
| Complétion indépendante | Nouvelle configuration et nouveau ledger, uniquement les 2 inspections manquantes : 4 tentatives fournisseur, 2 appels d'outils, 2 résultats retournés. |
| Cache local | Demande datée identique répétée dans la même session ; résultats identiques, sources réutilisées. Le cache n'est pas partagé entre sessions. |
| Couverture temporelle | Première fenêtre : 28 jours observés. Seconde : 27 sur 28 ; référence hebdomadaire indisponible pour couverture incomplète. Aucun jour absent transformé en zéro. |
| Codex natif | Version `0.162.0-alpha.17.2`, modèle demandé `gpt-6.1-sol`, effort élevé : 3 spécialistes, synthèse et reviewer séparé, 5 tentatives natives. |
| Claude Code natif | Version `2.1.296`, alias demandé `opus`, effort élevé : mêmes rôles et séquence, 5 tentatives natives. L'alias ne certifie pas une version de modèle concrète. |
| Entrée des modèles | Même projection privée de 43 692 bytes, SHA-256 `53173cd1615172a5780f368cedf39476fd8eda248ed7cb16f389e5c585052b98`. Agrégats, couverture, sitemaps, inspections et métadonnées pertinentes conservés ; ventilations page/requête et métadonnées dupliquées omises. |
| Appels pendant les lectures | Compteurs Google/outils inchangés ; total natif cumulé 10. Résultats `draft_and_review_returned; semantic_quality_unverified`. |

Le total des deux ledgers est de 24 tentatives fournisseur et 11 appels d'outils. La découverte de propriété et 3 contrôles HTTP publics séparés sont hors compteurs. Les tentatives ne mesurent ni le coût ni le nombre de succès ; l'acquisition auxiliaire HTML reste hors contrat du runner. La projection a été préparée par l'opérateur et relue via la bibliothèque existante sur un paquet sauvegardé. La CLI ne fournit pas de mode de revue d'un paquet sauvegardé. Les bytes d'acquisition originaux sont conservés et leurs hashes liés à cette projection ; elle ne remplace pas les preuves complètes.

La relecture indépendante a examiné 44 claims Codex et 79 claims Claude. Elle confirme les états GSC et les limites de couverture, sans approuver leur qualité SEO humaine. Une phrase de spécialiste Codex parle de « growth » malgré sa réserve sur la couverture ; le rapport opérateur conserve uniquement les différences arithmétiques. Deux références Claude à `/role_scope/observation_indices` ne se résolvent plus dans le paquet final ; le reviewer Claude détecte ce défaut. Une réserve sur les moyennes arithmétiques et une critique des références mixtes du reviewer Claude ont aussi été réfutées. Les sorties natives originales restent inchangées.

Le correctif natif refuse désormais `/role_scope` et ses descendants comme références, quel que soit le statut du claim, et précise cette limite dans le prompt. Ses régressions contrôlées passent ; les essais natifs originaux n'ont pas été rejoués après ce correctif. Ce contrôle structurel ne valide pas le soutien sémantique d'une affirmation.

La suite Python finale passe avec 2 081 tests. Les contrôles locaux du site et les 113 tests navigateur passent ; la documentation du runner et le changelog français sont synchronisés. Ces résultats ne prouvent ni une nouvelle publication PyPI ni un déploiement public de cette branche.

## Ce qui reste pour clôturer #39

Les [essais clients réalisés après ce pilote](2026-10-10-interactive-playbook-trials.md) ajoutent le chargement explicite de playbooks, des appels MCP de replay et deux revues de claims plantés. Ils restent distincts de cette acquisition réelle et de ses rôles source-only.

1. Traiter les écarts observés dans les essais clients et compléter leur périmètre restant. Le lot explicite headless ne prouve pas un dialogue humain multi-tour ni un routage implicite.
2. Étendre la revue de claims aux cas indépendants de #6. Les cinq affirmations synthétiques sont correctement classées par chaque reviewer ; ce résultat ne valide pas une qualité humaine ni une généralisation.
3. Conserver des cas de panne/reprise reproductibles et distinguer leurs fixtures des résultats authentifiés. Le pilote a réellement atteint un budget ; il n'a pas validé tous les modes de panne fournisseur.
4. Faire annoter des cas indépendants via #6 pour juger fidélité et diagnostic SEO. L'accord des modèles et les pointeurs valides ne constituent pas ce verdict.
5. Décider du périmètre d'acquisition HTML/CrUX avant une extension. Le pilote n'ajoute aucun de ces outils au runner.
