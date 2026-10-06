---
title: "Installation et configuration des clients MCP"
description: "Installer Search Console MCP une seule fois, le relier à un client et éviter les processus dupliqués."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/installation/
---

## Installation recommandée

Pour un essai ponctuel :

```bash
uvx gsc-mcp-tools
```

Pour une installation persistante :

```bash
uv tool install gsc-mcp-tools
```

Pour mettre à jour une installation existante :

```bash
uv tool upgrade gsc-mcp-tools
```

Vérifiez ensuite que le binaire est disponible :

```bash
gsc-cli --help
```

## Éviter les processus dupliqués

Le client MCP doit lancer le serveur à la demande via `stdio`. Ne démarrez pas manuellement un second serveur en arrière-plan. Gardez une seule définition `gsc-mcp` par client et utilisez le chemin absolu retourné par `which gsc-mcp-tools` si le client ne reprend pas votre `PATH`.

Après une modification de configuration, fermez complètement le client avant de le relancer. Si plusieurs clients sont ouverts, chacun peut avoir son propre processus enfant. C’est normal tant que les processus disparaissent à la fermeture des clients.

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

Vérifiez chaque fournisseur séparément. Une propriété Google visible ne prouve pas que Bing est configuré, et inversement. Contrôlez aussi la version réellement exécutée :

```bash
gsc-mcp-tools --version
```

## Diagnostic de consommation

Mesurez le nombre de processus avant et après l’ouverture d’un client, puis après sa fermeture. Le résultat attendu est un processus enfant par session MCP active, sans processus orphelin après fermeture. Une baisse de consommation doit être mesurée sur des fenêtres comparables, pas déduite du fichier de configuration.

[Lire la version anglaise canonique](/docs/installation/).
