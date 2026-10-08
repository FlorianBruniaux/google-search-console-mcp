---
title: "Audit SEO complet"
description: "Exécuter un audit multi-source structuré avec des limites de preuve explicites."
lang: fr
lastUpdated: 2026-10-06
canonicalEnglish: /docs/examples/full-audit/
---

```text
Réalise un audit SEO complet en lecture seule de https://yourdomain.com.

1. Inventorie les sources réellement configurées.
2. Analyse la performance Google et Bing sur des fenêtres comparables.
3. Audite le sitemap, robots.txt, les statuts HTTP, canonicals, métadonnées, titres et données structurées.
4. Analyse les liens internes et les pages isolées.
5. Utilise GA4 ou CrUX uniquement s’ils sont configurés et disponibles.
6. Classe les constats par impact observé, confiance et effort relatif.
7. Sépare faits, valeurs dérivées, hypothèses et actions proposées.

Ne lance aucun outil d’écriture sans confirmation distincte.
```

Le rapport doit conserver la source et la fenêtre avec chaque chiffre.

[Lire la version anglaise canonique](/docs/examples/full-audit/).

## Destinations HTTP dans le code source

`link_targets_audit(url, max_targets=30, max_requests=60)` observe les destinations internes d’une page affectée et conserve ses ancres. Les GET source et redirections partagent le budget. Un 404 reçu est observé ; timeout ou refus laisse le statut terminal indisponible. Consultez les [audits à périmètre borné](/fr/docs/audit-workflows/) pour interpréter une couverture partielle.
