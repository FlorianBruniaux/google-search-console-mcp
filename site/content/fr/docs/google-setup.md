---
title: "Configurer les accès Google"
description: "Configurer Search Console et les fournisseurs Google optionnels avec le minimum de droits."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/google-setup/
---

## Choisir le mode d’authentification

Utilisez un compte de service pour une intégration serveur stable ou OAuth pour un accès utilisateur interactif. Dans les deux cas, l’identité doit être ajoutée aux propriétés Search Console concernées.

## Compte de service

1. Créez ou sélectionnez un projet Google Cloud.
2. Activez l’API Search Console.
3. Créez un compte de service avec le minimum de droits nécessaire.
4. Téléchargez le fichier JSON dans un emplacement privé hors du dépôt.
5. Ajoutez l’adresse du compte de service comme utilisateur de chaque propriété Search Console cible.
6. Configurez le chemin du fichier dans l’environnement du serveur MCP.

Le fichier JSON est global pour l’identité. Les propriétés accessibles dépendent des permissions accordées dans Search Console.

## OAuth

OAuth convient quand un utilisateur doit autoriser directement l’accès. Conservez le secret client et les jetons hors du dépôt. Révoquez les jetons inutilisés depuis le compte Google.

## Fournisseurs optionnels

- GA4 nécessite une propriété Analytics et les droits associés.
- CrUX peut utiliser une clé API selon le workflow.
- PageSpeed Insights suit sa propre configuration et ses quotas.
- L’Indexing API n’est pas un mécanisme général d’indexation pour toutes les pages.

N’activez pas toutes les API par défaut. Configurez uniquement les familles de données nécessaires.

## Vérifier l’accès

```bash
gsc-cli list
```

Comparez la liste retournée aux propriétés attendues. Une absence peut venir de l’identité utilisée, du type de propriété ou d’un droit manquant. Ne remplacez pas cette vérification par une simple réussite d’authentification.

## Bonnes pratiques

- Gardez les secrets dans la configuration locale du client MCP.
- Accordez le niveau de permission minimal.
- Utilisez des propriétés de test pour les outils d’écriture.
- Révoquez les clés et jetons qui ne servent plus.

[Lire la version anglaise canonique](/docs/google-setup/).
