---
title: "Configurer Bing Webmaster Tools"
description: "Configurer la clé de compte Bing, vérifier les sites accessibles et distinguer IndexNow."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/bing-setup/
---

## Deux clés différentes

`BING_WEBMASTER_API_KEY` authentifie le compte Bing Webmaster Tools. Une même clé peut exposer plusieurs sites vérifiés visibles par ce compte. Chaque appel indique encore explicitement le `site_url` cible.

La clé IndexNow est différente. Elle est liée à un hôte et doit être publiquement vérifiable sur cet hôte. Ne réutilisez pas la clé de compte Bing comme clé IndexNow.

## Ajouter la clé de compte

Créez une clé dans Bing Webmaster Tools, puis ajoutez-la à l’environnement du serveur MCP :

```text
BING_WEBMASTER_API_KEY=...
```

Ne commitez jamais cette valeur et ne la collez pas dans une conversation publique.

## Vérifier les sites accessibles

Utilisez d’abord l’outil de liste des sites Bing. Vérifiez que les URL retournées correspondent exactement aux variantes attendues, notamment le protocole et le sous-domaine. Une clé valide ne garantit pas l’accès à un site non vérifié dans le compte.

## Écriture et IndexNow

Les soumissions sont bornées par une cible et une action explicites. Avant un envoi, confirmez le fournisseur, le site, les URL et la clé utilisée. Une réponse acceptée prouve la réception de la demande, pas un crawl ou une indexation.

## Diagnostic

- `401` ou `403` : contrôler la clé, le compte et les permissions du site.
- Site absent : vérifier la propriété dans Bing Webmaster Tools.
- IndexNow refusé : vérifier la clé sur l’hôte cible et l’URL du fichier de validation.
- Données vides : contrôler la fenêtre observée et la disponibilité du rapport avant de conclure à une absence de visibilité.

[Lire la version anglaise canonique](/docs/bing-setup/).
