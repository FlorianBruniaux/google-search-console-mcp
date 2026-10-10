---
title: "Installation et configuration des clients MCP"
description: "Installer Search Console MCP une seule fois, le relier à un client et éviter les processus dupliqués."
lang: fr
lastUpdated: 2026-10-11
canonicalEnglish: /docs/installation/
---

## Installation recommandée

La version 1.5.0 expose 96 outils, dont sept ajouts par rapport à 1.4.0.

Pour un essai ponctuel :

```bash
uvx gsc-mcp-tools
```

Pour une installation persistante :

```bash
uv tool install gsc-mcp-tools
```

Pour reproduire exactement cette version :

```bash
uv tool install --force gsc-mcp-tools==1.5.0
```

Une installation épinglée reste épinglée. Réinstallez sans contrainte de version avant d’utiliser `uv tool upgrade`, ou installez explicitement la prochaine version avec `--force`.

Pour mettre à jour une installation existante :

```bash
uv tool upgrade gsc-mcp-tools
```

Vérifiez ensuite que le binaire est disponible :

```bash
gsc-cli --help
```

## Exécuter les workflows source non publiés

Le paquet publié `gsc-mcp-tools==1.5.0` expose 96 outils et nécessite Python 3.11 ou ultérieur. L’audit natif borné et ses scripts d’évaluation nécessitent le checkout source actuel ; mettre à jour ce paquet publié n’installe pas ces ajouts non publiés.

Pour préparer le workflow source sans dépendances de développement :

```bash
git clone https://github.com/FlorianBruniaux/google-search-console-mcp.git
cd google-search-console-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
command -v gsc-mcp-tools
python scripts/run_bounded_audit.py --help
```

Si un client MCP doit utiliser ce checkout, configurez le chemin absolu `.venv/bin/gsc-mcp-tools`, puis redémarrez son serveur. Gardez une seule définition active par client. Pour contribuer et lancer les tests, installez les dépendances de développement avec `python -m pip install -e ".[dev]"`, puis lancez `pytest -q`.

Le [guide de l’audit natif borné](/fr/docs/bounded-native-audit/) décrit la propriété explicite, les requêtes en lecture seule, le dossier de sortie privé et les budgets de tentatives. L’acquisition seule ne lance aucun modèle. La génération native de rapports nécessite aussi un client CLI Codex ou Claude Code authentifié et un modèle pris en charge, choisi explicitement. Un run Google seul ne nécessite ni identifiants Bing ni identifiants GA4.

Les playbooks SEO interactifs du dépôt ont leurs fichiers canoniques dans `.agents/skills/`, projetés dans `.claude/skills/` pour Claude Code. Ouvrez le checkout comme espace de travail dans Codex ou Claude Code pour utiliser ces skills. Installer le paquet Python ou configurer Claude Desktop comme client MCP n’installe pas ces skills de dépôt. Le runner natif emploie des profils séparés de revue des sources, sans exécuter les playbooks interactifs. L’[index de validation](https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/docs/validation/README.md) distingue acquisition authentifiée, essais contrôlés des clients et contrôles humains restant à réaliser.

## Éviter les processus dupliqués

Le client MCP doit lancer le serveur à la demande via `stdio`. Ne démarrez pas manuellement un second serveur en arrière-plan. Gardez une seule définition `gsc-mcp` par client et utilisez le chemin absolu retourné par `which gsc-mcp-tools` si le client ne reprend pas votre `PATH`.

Après une modification de configuration, fermez complètement le client avant de le relancer. Si plusieurs clients sont ouverts, chacun peut avoir son propre processus enfant. C’est normal tant que les processus disparaissent à la fermeture des clients.

## Choisir les familles MCP (depuis 1.3.1)

Depuis la version 1.3.1, `GSC_MCP_TOOL_FAMILIES` accepte une liste de familles séparées par des virgules. La version 1.3.0 précède cette option. Pour une session SEO Google ciblée, ajoutez cette variable non secrète à l’environnement du serveur :

```text
GSC_MCP_TOOL_FAMILIES=analytics,seo,sitemaps,links
```

Les familles disponibles sont `analytics`, `seo`, `inspection`, `indexing`, `sitemaps`, `ga4`, `cross`, `crux`, `technical`, `drift`, `content`, `editorial`, `links`, `bing` et `core`. Une variable absente ou égale à `all` expose tout le catalogue. `core` reste présent dans chaque sélection. Une sélection vide ou un nom inconnu empêche le démarrage.

Redémarrez le serveur ou le client MCP après tout changement, puis vérifiez sa liste réelle d’outils. Le processus conserve sa sélection de démarrage. `gsc-cli list` continue d’afficher le catalogue complet.

La sélection contrôle la découverte MCP, sans accorder d’identifiants, de permissions fournisseur ou d’autorisation d’écriture. Ajoutez seulement les identifiants des fournisseurs utilisés. Une réponse de découverte plus petite ne prouve pas une économie précise de tokens ; celle-ci dépend du client et de son tokenizer.

## Variables minimales

Le serveur peut démarrer sans tous les fournisseurs. Ajoutez seulement les variables correspondant aux services utilisés :

- Google Search Console : chemin vers le compte de service ou jeton OAuth documenté dans le [guide Google](/fr/docs/google-setup/).
- Bing Webmaster Tools : `BING_WEBMASTER_API_KEY`, documentée dans le [guide Bing](/fr/docs/bing-setup/).
- IndexNow : clé séparée et vérifiable sur chaque hôte cible.

Ne placez jamais une valeur secrète dans un prompt ou un dépôt Git.

## Configuration du client

Utilisez la commande installée comme exécutable MCP et passez les secrets dans l’environnement du serveur. Le nom exact du fichier de configuration dépend du client. Le transport attendu est `stdio`.

## Vérification

```bash
gsc-cli list
```

Vérifiez chaque fournisseur séparément. Une propriété Google visible ne prouve pas que Bing est configuré, et inversement. Pour une installation persistante via uv, contrôlez aussi la version installée :

```bash
uv tool list
```

## Listes d’URL dans la CLI

Répétez `--urls` pour fournir plusieurs URL. Depuis la version 1.3.1, la CLI accepte aussi un tableau JSON de chaînes :

```bash
gsc-cli batch-url-inspection --site https://example.com/ \
  --urls https://example.com/a --urls https://example.com/b
gsc-cli batch-url-inspection --site https://example.com/ \
  --urls '["https://example.com/a","https://example.com/b"]'
```

Les virgules restent littérales : `--urls 'https://example.com/a,b?q=x,y'` transmet une seule URL. Un tableau malformé ou contenant autre chose que des chaînes est refusé avant tout appel fournisseur. Le format JSON pour ces listes est disponible depuis 1.3.1 ; les options répétées fonctionnent aussi dans 1.3.0.

## Diagnostic de consommation

Mesurez le nombre de processus avant et après l’ouverture d’un client, puis après sa fermeture. Le résultat attendu est un processus enfant par session MCP active, sans processus orphelin après fermeture. Une baisse de consommation doit être mesurée sur des fenêtres comparables, pas déduite du fichier de configuration.

[Lire la version anglaise canonique](/docs/installation/).
