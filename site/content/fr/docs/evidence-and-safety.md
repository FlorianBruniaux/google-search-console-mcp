---
title: "Preuves et sécurité"
description: "Interpréter les résultats sans confondre observation, calcul, soumission, crawl et indexation."
lang: fr
lastUpdated: 2026-10-07
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
