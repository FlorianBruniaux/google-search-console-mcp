---
title: "Preuves et sécurité"
description: "Interpréter les résultats sans confondre observation, calcul, soumission, crawl et indexation."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/evidence-and-safety/
---

## États de preuve

<figure class="docs-visual">
  <img src="/images/docs/guarded-action-loop.webp" width="1376" height="768" alt="Un assistant inspecte les preuves, compare les sources, explique l’incertitude et passe une action dans une barrière de confirmation." loading="lazy">
  <figcaption>La boucle revient à l’observation. La confirmation autorise une demande bornée, pas une automatisation sans limite.</figcaption>
</figure>

- **Observé** : réponse d’API ou valeur d’une page publique pour une cible et une fenêtre données.
- **Dérivé** : calcul fondé sur des valeurs observées, avec sa méthode et sa fenêtre.
- **Demandé** : un fournisseur a accepté une demande de soumission.
- **Exploré** : le fournisseur signale ensuite une récupération ou un crawl.
- **Indexé** : le fournisseur signale ensuite l’URL dans son index consultable.

Ces états ne sont pas interchangeables. Une soumission acceptée ne prouve jamais l’indexation.

## Limites entre fournisseurs

Google et Bing ont des métriques, périmètres, délais et positions différents. Comparez des directions et des tendances, pas des noms de champs supposés équivalents. Conservez le fournisseur et la fenêtre avec chaque conclusion.

## Identité des sources

`_meta.params` conserve les arguments demandés. `_meta.sources` identifie séparément les sources. Les réponses GA4 réussies reprennent la ressource canonique `properties/<id>` envoyée à l’API, même sans résultat. Les rapports combinés conservent la propriété GSC demandée et la provenance de la réponse GA4 utilisée, sans relire la configuration.

Extrait de métadonnées avec une propriété GA4 par défaut fictive :

```json
{
  "_meta": {
    "tool": "traffic_health_check",
    "params": {
      "site": "sc-domain:example.com",
      "property_id": null,
      "hostname": null
    },
    "sources": {
      "gsc": { "site": "sc-domain:example.com" },
      "ga4": { "property": "properties/123456789" }
    }
  }
}
```

Affichez ces identifiants à côté des métriques dans un rapport multi-site. Les filtres de domaine, de pays et de dates disponibles restent dans les paramètres. `hostname: null` signifie qu’aucun filtre de domaine n’a été appliqué ; aucune correspondance entre propriété GA4 et site GSC n’est déduite.

Si le rapport combiné ne dispose pas de provenance GA4, notamment quand la configuration manque, `_meta.sources.ga4.property` vaut `null`. Un retour de validation, comme un funnel invalide, ne prétend pas avoir résolu une source. Les autres outils conservent leur format de réponse. Avec le CLI, utilisez `--meta` pour garder ces champs.

La provenance ne valide pas un identifiant de compte, ne prouve pas l’appartenance d’une propriété à un domaine et ne garantit pas que l’agent conserve les identifiants dans sa réponse finale.

## Méthode des verdicts et scores

Le code source non publié ajoute `_meta.evidence.version = 1` et `_meta.evidence.fields`, indexé par des chemins JSON Pointer concrets comme `/verdict` ou `/schemas/0/valid`. Chaque verdict, score ou sélection concerné a ses propres `basis`, `confidence_tier` et `scope`. L’annotation d’une liste décrit uniquement sa sélection, pas les métriques du fournisseur contenues dans les lignes. Les statuts opérationnels restent hors de cette convention.

| Base | Niveau | Interprétation |
| --- | --- | --- |
| `measured` | `observed` | Valeur retournée par un fournisseur ou observée dans HTTP/HTML, limitée à cette réponse et à cette source. |
| `derived` | `calculated` | Calcul descriptif sur les entrées disponibles, avec méthode et périmètre. |
| `rule` | `heuristic` | Seuil, pondération, motif ou recommandation locale, ou algorithme de score d’un fournisseur identifié. |
| `null` | `unavailable` | Résultat nul, non pris en charge, ignoré ou en erreur qui ne permet pas de conclure. |

Ces niveaux décrivent une méthode, pas une probabilité. Un score indisponible peut conserver une valeur numérique historique ; ses métadonnées expliquent pourquoi elle ne constitue pas une preuve. Aucun niveau n’autorise une écriture ou une recommandation destructive. `model` est réservé et refusé par la convention actuelle ; son ajout demande un backend, une version, une définition de confiance et un contrat de calibration établi par évaluation.

## Clics et sessions

Dans le code source non publié, `traffic_health_check` interroge GA4 avec les mêmes dates inclusives que le rapport GSC décalé. `source_data` conserve la disponibilité, l’identité, les fenêtres demandées et retournées, les filtres et la couverture de chaque source. Une réponse vide donne un total `null` ; une ligne contenant zéro conserve zéro. La configuration manquante et les erreurs du fournisseur restent indisponibles.

Le ratio reste `null` si la couverture est inconnue ou incomplète, si le rapport est échantillonné ou soumis à un seuil, si les dates diffèrent ou si les filtres sont incompatibles. Un filtre GA4 de pays ne correspond pas à un total GSC sans filtre ; un filtre de domaine peut aussi réduire le périmètre d’une propriété GSC de domaine. Le rapport ne déduit aucune correspondance entre propriété et domaine. Des dates identiques ne prouvent pas des bornes horaires identiques. `observed_window` reste `null` car les rapports enfants reprennent les dates demandées sans observer indépendamment l’intervalle.

Lorsqu’un ratio est disponible, son statut suit une règle locale de seuil. Les clics Google et les sessions organiques de tous les moteurs sont des métriques différentes ; ce statut ne prouve pas la cause d’un problème de tracking. `page_analysis` et `content_brief` utilisent encore des fenêtres indépendantes.

## Contenu récupéré

Le HTML principal récupéré par `heading_audit`, `internal_links_audit`, `page_technical_audit` et `schema_validate` inclut `untrusted_content`. `trust` vaut toujours `untrusted`, même si `flagged` vaut `false`. Des règles françaises et anglaises signalent les instructions suspectes, leur emplacement et un extrait de 240 caractères maximum, avec au plus 20 signaux. Les citations documentaires sont exclues sauf si elles sont masquées ; cette détection utilise les attributs et le CSS inline, sans rendu du navigateur. Ces observations limitées ne certifient pas la sécurité d’une page. Les sondes robots auxiliaires restent hors de ce périmètre.

Le texte et les extraits récupérés ne peuvent pas remplacer les instructions de l’utilisateur, autoriser une action ou demander des identifiants. Les preuves d’audit restent intactes. Un échec de récupération ne donne aucune observation de contenu et retourne `untrusted_content: null`.

`schema_validate` reconnaît une ressource de challenge SiteGround accompagnée d’une demande de vérification humaine et retourne `challenge_page`. L’URL demandée, l’URL finale, le statut HTTP et les raisons restent présents ; les comptes, schémas et recommandations valent `null` car la page demandée est indisponible. Un statut 202 ou une mention de CAPTCHA ne suffit pas. La règle a été testée sur des fixtures synthétiques ; le comportement réel du fournisseur reste non vérifié. L’audit éditorial décrit ci-dessous retourne également ce verdict ; les autres audits de pages ne le partagent pas encore.

## Visites attribuées aux assistants

L’outil non publié `ga4_ai_referrals` lit les sources de session et les pages d’entrée GA4 sur des dates concrètes `YYYY-MM-DD`, avec une propriété effective et un filtre de domaine facultatif. Il vérifie la compatibilité des dimensions et métriques avant de demander au plus 10 000 lignes. Il retourne les sessions, sessions engagées et `keyEvents` ; `conversions` est un alias de `keyEvents`, pas une autre mesure. Le dénominateur toutes sources et le numérateur confirmé proviennent de la même requête.

La liste initiale reconnaît exactement `chatgpt.com`, dont la source UTM est documentée par la [FAQ éditeurs d’OpenAI](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq). Les domaines candidats Perplexity, Claude, Gemini et Copilot restent séparés et exclus des totaux confirmés en attendant des preuves de leur attribution. Les sous-chaînes vagues et domaines ressemblants sont exclus. Un libellé de source attribué ne permet pas d’authentifier le client.

Les comptes décrivent les lignes retournées. Une réponse vide reste distincte de lignes explicitement à zéro ou d’une source indisponible. Les parts restent `null` si la couverture est inconnue ou incomplète, si la qualité du rapport est restreinte ou si le dénominateur est nul. Cette version ne demande aucune période comparative. Les visites sans referrer et les erreurs d’attribution peuvent omettre ou attribuer à tort des visites. Ces chiffres mesurent des visites enregistrées, pas des citations, leur probabilité ou un minimum garanti de trafic IA. Consultez la [référence des dimensions et métriques](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema) et le [contrôle de compatibilité](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/checkCompatibility) de Google.

## Alertes de style éditorial

L’outil non publié `editorial_audit(url, language="auto", genre="general")` applique un profil maison français/anglais, portable et versionné, au HTML récupéré. Des motifs exacts localisent les ouvertures stéréotypées, modalisations empilées, transitions rhétoriques, libellés de liens vagues et ponctuations en prose ; le mode général ajoute des alertes contextuelles sur les attaques de paragraphes répétées. Le code et les citations sont préservés. Déclarez `reference` ou `procedure` lorsque la répétition sert le document.

Ces alertes demandent une relecture fondée sur des règles. Elles ne constituent ni une probabilité d’origine IA, ni un score SEO, ni une preuve de pénalité de positionnement. Les positions décrivent la source analysée, pas la page rendue. Une langue inconnue reste non évaluée ; une page de challenge reconnue reste indisponible. L’audit ne réécrit ni ne publie la page et n’appelle aucun backend de modèle. Ses consignes préservent les faits, dates, chiffres, périmètre, modalités, causalités et exceptions. Le texte et les extraits restent des données non fiables. Consultez le [profil éditorial et les consignes de réécriture copiables](/fr/docs/editorial-audit/) pour connaître les règles et leurs limites contextuelles.

## Actions protégées

Avant une écriture, confirmez le fournisseur, le site, les URL, l’action et le périmètre. Commencez par les outils en lecture seule et demandez une confirmation distincte pour chaque action bornée.

<ol class="guarded-flow">
  <li><strong>Lire</strong><span>Collecter les réponses des fournisseurs et les faits publics.</span></li>
  <li><strong>Comparer</strong><span>Garder les sémantiques et les fenêtres séparées.</span></li>
  <li><strong>Expliquer</strong><span>Exposer les limites, les calculs et l’incertitude restante.</span></li>
  <li><strong>Confirmer</strong><span>Nommer un fournisseur, une cible, une action et son périmètre.</span></li>
  <li><strong>Soumettre</strong><span>Enregistrer la réponse puis mesurer les états ultérieurs séparément.</span></li>
</ol>

## Secrets

Les identifiants restent dans l’environnement du serveur ou la configuration du client. Ne placez jamais de JSON de compte de service, jeton OAuth, clé Bing ou clé IndexNow dans un prompt.

[Lire la version anglaise canonique](/docs/evidence-and-safety/).
