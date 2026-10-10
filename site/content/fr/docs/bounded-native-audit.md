---
title: "Audits natifs depuis un checkout source"
description: "Exécuter le workflow natif non publié avec des sources explicites, des budgets de tentatives et des limites de preuves."
lang: fr
lastUpdated: 2026-10-11
canonicalEnglish: /docs/bounded-native-audit/
---

Ce workflow source optionnel acquiert une fois un plan explicite de requêtes en lecture seule, puis transmet des observations immuables aux spécialistes sélectionnés, à un auteur de rapport et à une invocation séparée de revue. Les deux clients CLI natifs utilisent les mêmes contrats de profils. Le workflow ne fournit ni l’ancien hôte JavaScript Workflow, ni le routage interactif des skills, ni l’acquisition auxiliaire HTML/CrUX. La qualité experte des rapports dépend encore des cas humains de #6.

Ces changements source ne sont pas publiés. Utilisez un checkout qui les contient et son environnement Python ; le wheel publié 1.5.0 seul ne fournit pas ce workflow. La découverte MCP par défaut reste inchangée à 96 outils. Les prototypes de requêtes n’ajoutent aucun outil MCP.

Les [exécutions hors ligne enregistrées](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-native-specialists.md) du 10 octobre 2026 ont chacune utilisé 4 tentatives natives, 2 appels locaux aux outils et 0 tentative fournisseur, sous des identifiants séparés pour Codex et Claude. Ces observations historiques ne décrivent pas une acquisition actuelle auprès de fournisseurs authentifiés. Les [contrôles de ressources ultérieurs](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-delegated-evaluation-native-limits.md) testent séparément des enfants locaux sans effet métier et le comparateur d’extraction hors ligne.

## Checkout source et prérequis

Le [pilote GSC authentifié](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-10-live-gsc-readiness.md), enregistré séparément, décrit l’acquisition Google réelle et les revues natives de projections privées identiques, avec couverture partielle et limite de budget fournisseur. Le [suivi C1](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/2026-10-11-claude-c1-followup.md) décrit huit cas contrôlés de playbook interactif réussissant uniquement leurs critères figés sur les comptes manquants. Il utilise des réponses MCP rejouées, sans nouvelle acquisition fournisseur. Ces parcours de validation restent distincts ; aucun n’approuve l’exactitude du rapport entier ni sa qualité SEO évaluée par des humains, et #39 reste ouverte.

Utilisez Python 3.11 ou ultérieur depuis la racine du dépôt. Sous Linux ou macOS, préparez un environnement source :

```sh
git clone https://github.com/FlorianBruniaux/google-search-console-mcp.git
cd google-search-console-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Les invocations natives nécessitent aussi un client Codex ou Claude installé et authentifié, avec un modèle pris en charge par ce client. Le mode natif prend en charge Linux et macOS. Le mode acquisition seule ne lance pas de sous-processus natifs ; suivez les [prérequis d’installation](/fr/docs/installation/). Ces commandes de préparation n’accordent aucun accès fournisseur et n’autorisent pas les appels aux modèles. Les exécutions hors ligne décrites ci-dessous ne vérifient ni la qualité humaine des rapports ni l’acquisition auprès de fournisseurs authentifiés.

Pour des cibles de qualité indépendantes, utilisez la [collecte d’évaluations humaines](/fr/docs/expert-evaluation-intake/). L’[évaluateur des requêtes](/fr/docs/classifier-evaluation/) et la [comparaison locale d’extraction](/fr/docs/content-extraction/#comparaison-hors-ligne-avec-annotations) emploient des annotations distinctes et ne certifient pas la qualité des rapports natifs.

## Préparer une exécution explicite

Créez un dossier privé existant pour le journal persistant et les rapports dont vous êtes responsable. La configuration n’est pas un fichier d’identifiants et n’est jamais installée globalement.

```json
{
  "run_id": "my-reviewed-audit",
  "site": "sc-domain:example.com",
  "bing_site": "https://example.com/",
  "ledger_path": "/absolute/private-directory/run.sqlite",
  "max_provider_attempts": 20,
  "max_tool_calls": 20,
  "max_native_calls": 6,
  "allowed_tools": ["get_capabilities", "get_search_analytics", "indexing_evidence_matrix"]
}
```

`example.com` et le chemin sont des exemples à remplacer par la propriété autorisée et un vrai chemin privé absolu. Une configuration limitée à Google peut omettre `bing_site` ; autoriser un outil Bing ou `compare_search_engines` exige son URL explicite et valide. Retirer ce champ d’une configuration déjà enregistrée change son identité et nécessite un nouvel ID. Sélectionner un outil n’accorde aucun accès fournisseur. Les outils GA4 nécessitent aussi `ga4_property`, par exemple `"123456789"` ; la propriété explicite de l’appelant remplace les valeurs GA4 ambiantes, et les arguments contradictoires sont refusés.

Le fichier de requêtes est un tableau JSON d’enregistrements `{tool, arguments}`. Exemple hors ligne :

```json
[
  {
    "tool": "indexing_evidence_matrix",
    "arguments": {
      "site": "sc-domain:example.com",
      "urls": ["https://example.com/page"]
    }
  }
]
```

```sh
python scripts/run_bounded_audit.py --config /absolute/config.json \
  --requests /absolute/requests.json --output /absolute/new-report.json
```

Cette commande acquiert le plan déclaré, sans invocation de modèle par défaut. Le périmètre de chaque requête est vérifié avant la première acquisition. La CLI impose `GSC_NO_BROWSER=1` ; préparez séparément l’authentification si elle manque. Elle refuse avant acquisition une sortie existante ou un lien symbolique, ainsi qu’un dossier parent absent. Les écritures et les outils absents de la liste sont refusés. Les exceptions fournisseur restent indisponibles à côté des autres résultats. La sortie est créée avec un accès privé ; un fichier existant n’est jamais remplacé.

## Auteur et relecteur natifs optionnels

Ajoutez `--host codex --model gpt-6.1-sol` à la commande. Cette combinaison client/modèle a terminé l’exécution source synthétique hors ligne du 10 octobre 2026. L’adaptateur utilise un raisonnement high, des sessions éphémères, un dossier de travail temporaire vide, ignore la configuration utilisateur Codex, active un sandbox en lecture seule et désactive la recherche Web. Il demande au modèle d’utiliser uniquement le paquet ; le sandbox Codex permet encore les commandes en lecture seule. Cela ne constitue pas une interdiction générale de toute invocation d’outil.

`--host claude --model <caller-supported-Claude-model>` utilise un effort high, aucun outil intégré et une configuration MCP stricte vide. Le client Claude installé a terminé le parcours auteur/relecteur avec sources hors ligne le 10 octobre 2026, en utilisant son alias `opus` pris en charge et l’effort high. Cette observation concerne ce parcours du paquet, sans établir la précision du diagnostic ni une acquisition SEO authentifiée. Fournissez un modèle pris en charge par ce client natif, plutôt qu’un alias Codex ; l’alias `opus` peut changer de résolution après une mise à jour du client.

Sans spécialiste, le parcours tente un appel auteur, puis un appel distinct de revue. La configuration optionnelle `max_native_calls` borne les réservations natives par exécution de 1 à 64, avec une valeur par défaut de 2. Chaque invocation réserve avant lancement, même en cas d’échec ; rouvrir une exécution poursuit ce compteur. Ce plafond concerne ce parcours orchestré, pas les autres sessions CLI. Il compte les tentatives, pas les tokens, le coût facturé ou la durée. Ajouter ce réglage à une configuration immuable existante exige un nouvel identifiant d’exécution. Les invocations antérieures à ce compteur ne sont pas reconstituées.

Les erreurs du client conservent les observations acquises et rendent la branche concernée indisponible. Les faits déclarés soutenus nécessitent un pointeur dans les observations acquises ; une référence au brouillon ou à un spécialiste ne suffit pas. Le validateur structurel vérifie la forme des affirmations et les limites des sources, sans établir leur fondement sémantique. Les annotations humaines ne sont pas fournies aux modèles. Les appels aux modèles natifs sont comptés séparément des tentatives fournisseur ; aucun coût mesuré ni précision diagnostique n’est revendiqué.

## Spécialistes source optionnels

Répétez `--specialist` pour choisir explicitement les profils, et ajoutez éventuellement `--max-native-concurrency 2`. La borne de concurrence accepte 1..4, vaut 1 par défaut et s’applique à ce pipeline ; la synthèse et la revue restent séquentielles. Chaque profil utilise le modèle explicite de l’appelant et un raisonnement/effort high. Aucun alias propre à un client n’est copié dans la configuration d’un autre.

```sh
python scripts/run_bounded_audit.py --config /absolute/config.json \
  --requests /absolute/requests.json --output /absolute/new-report.json \
  --host codex --model gpt-6.1-sol \
  --specialist gsc-indexing-auditor --specialist gsc-sitemap-auditor \
  --max-native-concurrency 2
```

Les neuf projections de `src/gsc_mcp/native_roles.py` correspondent aux noms des profils SEO du dépôt :

| Profil | Sources fournies utilisées et limite conservée |
| --- | --- |
| `gsc-seo-reporter` | Performances, comparaisons de périodes, alertes ; aucun score de santé ou pénalité inventé |
| `gsc-traffic-doctor` | Comparaisons datées, candidats trafic et références quotidiennes ; les causes restent des hypothèses |
| `gsc-ai-overviews-analyst` | Observations génériques de recherche ; exposition IA et perte causale indisponibles sans source |
| `gsc-indexing-auditor` | Inspections sélectionnées et matrices de preuves ; verdicts inconnus et limites d’échantillon explicites |
| `gsc-sitemap-auditor` | Inventaire des sitemaps soumis et inspections séparées ; aucun ratio soumis/indexés |
| `gsc-schema-auditor` | Validation de schéma fournie ; la liste d’acquisition exclut l’outil HTML auxiliaire, donc la CLI actuelle la marque indisponible |
| `gsc-cannibalization-checker` | Recoupement requêtes/pages et inspections ; le recoupement seul ne justifie pas une consolidation |
| `gsc-content-optimizer` | Opportunités sélectionnées par règles et requêtes récupérées ; aucun gain de classement promis |
| `gsc-page-analyst` | Performances de page et inspections fournies ; HTML, schémas, rendu et métriques vitales manquants restent indisponibles |

Ces contrats de revue des sources sont plus étroits que les profils interactifs de `.claude/agents/`. Ils ne chargent ni n’exécutent les playbooks et n’activent pas leurs outils MCP. La sélection n’ajoute jamais de requête d’acquisition. Un spécialiste reçoit une nouvelle copie décodée des observations originales, avec les indices utilisables déclarés dans `role_scope` ; la validation refuse les pointeurs vers d’autres observations ou vers la collection entière. Les références au contexte temporaire `role_scope` sont refusées pour tous les statuts d’affirmation, car ce champ est absent du paquet final. Les indices originaux restent stables. Cette limite de références n’est ni une preuve sémantique ni un filtre de confidentialité : le paquet original est visible au modèle sélectionné.

Sources manquantes, sources en échec, échecs de modèle et budgets épuisés ont des motifs d’indisponibilité distincts à côté des branches réussies. Les spécialistes laissent deux places actuellement disponibles pour la synthèse/revue. Un autre processus partageant l’exécution peut les consommer ; le plafond persistant refuse toujours l’envoi avant des tentatives excédentaires. Un processus redémarré peut acquérir à nouveau sous le budget fournisseur, car les observations ne sont mises en cache que dans une session d’acquisition.

Le paquet final conserve `specialists`, `draft`, `review`, le client/modèle/effort/concurrence explicites et les compteurs cumulés. `partial; semantic_quality_unverified` signifie qu’au moins une branche sélectionnée était indisponible ; la revue retournée n’approuve aucun changement du site. Une branche de schéma indisponible n’établit pas la validité du schéma. Deux rapports générés concordants ne remplacent pas une évaluation humaine indépendante.

Chaque rapport généré conservé est limité à 128 000 octets JSON UTF-8. Avec neuf profils distincts plus l’auteur et le relecteur, les corps conservés ne peuvent pas dépasser 1 408 000 octets au total. Les rapports trop grands deviennent une branche indisponible avant agrégation, sans tronquer les preuves source. L’entrée de synthèse/revue conserve le plafond de paquet de 2 MB ; si les sources et le contenu généré le dépassent, cette branche est indisponible et les observations restent conservées. Les types d’affirmation malformés ou une enveloppe Claude malformée échouent aussi uniquement dans leur branche.

Sous Linux et macOS, l’exécution native borne stdout et stderr séparément à 2 000 000 octets pendant l’exécution de l’enfant. Stdout est conservé dans une mémoire bornée ; stderr est compté puis éliminé. Aucun flux n’est écrit dans un journal disque. Dépasser l’un des plafonds arrête l’invocation et rend sa branche indisponible, avec conservation des observations et de la réservation persistante. La sortie de l’enfant n’est jamais copiée dans les messages d’échec.

Un lanceur Python séparé installe un plafond dur `RLIMIT_FSIZE` hérité d’au plus 2 000 000 octets avant d’exécuter le client. Cela borne le fichier final Codex au niveau des écritures du noyau, y compris entre les contrôles de surveillance. Un fichier final atteignant 2 000 000 octets est refusé par précaution. Ce plafond par fichier s’applique aussi aux autres fichiers ordinaires écrits par le client natif ou ses descendants, notamment l’état du client hors du dossier temporaire ; ce n’est ni un quota disque agrégé ni une limite mémoire du client. Les limites souples ou dures héritées plus faibles sont conservées dans le plafond dur de l’enfant. Les clients nécessitant des fichiers plus grands peuvent devenir indisponibles sous ce prototype.

Chaque invocation démarre un nouveau groupe de processus. Fin, expiration du délai et dépassement de sortie tuent les membres restants de ce groupe et attendent l’enfant direct avant de nettoyer les fichiers temporaires. Les descendants qui se détachent délibérément dans un autre groupe sont hors de cette garantie ; le système d’exploitation récupère les descendants orphelins. Les spécialistes concurrents utilisent des lanceurs et groupes distincts, sans changer les limites du parent ni utiliser un `preexec_fn` dans un contexte multithread. Les autres plateformes sont explicitement indisponibles pour l’exécution native ; les exécutions limitées à l’acquisition restent disponibles. Ces limites utilisent les [sessions de processus et options de lancement compatibles avec les threads](https://docs.python.org/3/library/subprocess.html#subprocess.Popen), les [limites de fichiers](https://docs.python.org/3/library/resource.html#resource.RLIMIT_FSIZE) et les [signaux aux groupes](https://docs.python.org/3/library/os.html#os.killpg) documentés par Python.

Des tests locaux avec des enfants Python sans effet métier couvrent le dépassement actif de stdout/stderr, un rédacteur de fichier final qui intercepte son erreur d’écriture, le délai, le nettoyage des descendants, les invocations concurrentes et les enveloppes des deux clients. Ces fixtures exercent la gestion des ressources, pas une exécution réelle de fournisseurs Claude/Codex ni la précision diagnostique.

## Contrat de budget et de cache

Le journal SQLite de l’appelant réserve atomiquement les tentatives sous un même identifiant d’exécution entre sessions/processus. Une configuration modifiée pour cet identifiant est refusée. Le journal ne se réinitialise pas au redémarrage. Réutiliser l’identifiant poursuit son budget ; choisissez un nouvel identifiant explicite pour une nouvelle exécution. Supprimez un journal uniquement lors d’un nettoyage explicite de l’appelant, lorsque ses enregistrements ne sont plus nécessaires.

L’envoi HTTP Google est compté à la frontière de requête de la connexion, y compris les retries internes httplib2 et les répétitions liées aux identifiants dans ce transport. La préparation de connexion avant envoi HTTP, la résolution isolée des identifiants, les autres clients réseau et les acquisitions auxiliaires HTML/CrUX sont hors de ce contrat. Les retries Bing réservent avant chaque tentative HTTP. Les clients GA4 sous budget désactivent les retries transparents GAPIC et gRPC ; chaque envoi RPC réserve une tentative. Les envois en échec sont conservés. La liste autorisée exclut les outils nécessitant des acquisitions auxiliaires non comptées. Les fixtures de transport ne sont pas de nouvelles mesures fournisseur.

L’acquisition dans une session est sérialisée. Des requêtes identiques concurrentes reçoivent une réponse JSON immuable ; modifier une copie décodée ne peut pas changer la chaîne en cache. Le cache est propre à la session, borné à 8 MB au total et 2 MB par observation, sans persistance. Un autre processus peut acquérir à nouveau les données, sous le même plafond persistant de tentatives. Les appels aux outils, y compris les lectures du cache, ont une borne séparée. Le journal conserve des comptes de réservations, pas des mesures détaillées de temps ni une preuve de succès fournisseur.

Pour exposer uniquement les outils d’audit sélectionnés dans un processus MCP dédié, définissez `GSC_MCP_AUDIT_CONFIG=/absolute/config.json` dans son environnement avant de le démarrer. Cela change uniquement la surface de démarrage de ce processus. Ce dépôt ne modifie aucun réglage client ni fichier global de skill. La découverte renvoie la liste réduite effective et le périmètre de budget.

## Évaluation humaine des rapports

`scripts/eval_audit_reports.py` traite trois axes de revue des affirmations : diagnostic de trafic, concurrence nuisible et fidélité des rapports. Il est séparé de la classification des requêtes et ne mesure ni inclusion/omission d’extraction ni similarité entre pages.

Chaque corpus déclare `schema_version: 1`, `corpus_id`, `provenance` (`human` ou `synthetic`) et `cases`. Chaque cas fournit un identifiant, une famille, un split, un axe, la langue FR/EN, les observations source, les affirmations revues et la provenance des annotations. Une annotation nomme des identités distinctes d’annotateur/relecteur, l’autorisation source et la résolution des désaccords. Les labels sont `supported`, `unsupported` ou `unresolved`, chacun avec des références qui se résolvent dans les observations du cas. Les familles liées ne peuvent pas traverser les splits train/tuning/held-out.

```sh
python scripts/eval_audit_reports.py --dataset /absolute/reviewed-corpus.json --prepare
python scripts/eval_audit_reports.py --dataset /absolute/reviewed-corpus.json \
  --predictions /absolute/independent-claim-predictions.json
```

La préparation émet seulement les observations sélectionnées et les identifiants de cas/tâche, sans les affirmations attendues ni les labels humains. Les prédictions fournissent l’identifiant du corpus, le split, une identité de relecteur indépendant et des lignes avec `case_id`, `claim_id`, `label`. Les prédictions manquantes restent dans le dénominateur complet ; les comptes par axe exposent les erreurs « non soutenu déclaré soutenu ». Ces identités sont déclarées par l’appelant, pas des identités humaines vérifiées. Le contrôle de publication reste indisponible tant que les cibles par tâche et une décision humaine d’approbation ne sont pas fournies hors de ce cadre.

## Prototypes de requêtes hors ligne

`scripts/query_rules_baseline.py` produit des prédictions d’intention compatibles avec l’évaluateur existant. Il lit le texte/langue et les marques fournies par l’appelant, pas les labels de référence. Le prototype par règles sépare la forme interrogative de l’intention et s’abstient devant des signaux lexicaux mixtes ou négatifs. `query_rules.near_query_candidates` conserve les variantes et l’ordre, et marque l’égalité d’intention inconnue. Il ne trie pas les tokens, ne supprime pas les négations et ne fusionne pas silencieusement Paris/Londres avec Londres/Paris.

```sh
python scripts/query_rules_baseline.py --dataset /absolute/query-corpus.json \
  --split held_out --brand-terms '["caller-brand"]' > /absolute/predictions.json
python scripts/eval_classifier.py --dataset /absolute/query-corpus.json \
  --predictions /absolute/predictions.json
```

Les deux prototypes restent hors du registre public. Les sorties synthétiques sont inéligibles à la publication et ne mesurent pas la qualité sur de vraies requêtes FR/EN. #4/#5 nécessitent encore une taxonomie, des seuils et des résultats held-out approuvés par des humains. Aucun embedding ni backend de classification payant n’est ajouté.
