---
title: "Investigation d’une chute de trafic"
description: "Comparer des fenêtres équivalentes et localiser les contributions à une variation."
lang: fr
lastUpdated: 2026-10-09
canonicalEnglish: /docs/examples/traffic-drop/
---

```text
Investigue la baisse de trafic de https://yourdomain.com.

- Compare les 28 derniers jours aux 28 jours précédents.
- Mesure séparément clics, impressions, CTR et positions.
- Décompose la variation par pages, requêtes, appareils, pays et fournisseurs.
- Vérifie les changements techniques publics et les états d’indexation disponibles.
- Utilise GA4 seulement pour compléter, jamais pour remplacer les données de recherche.
- Classe les causes possibles par preuve disponible.

Ne présente pas une corrélation comme une causalité prouvée.
```

[Lire la version anglaise canonique](/docs/examples/traffic-drop/).

Avec la version 1.4.0, utilisez `search_change_breakdown` pour les fenêtres inclusives du 2026-09-01 au 2026-09-07 et du 2026-09-08 au 2026-09-14. Conservez chaque dimension séparément : une ligne absente reste inconnue, une contribution ne prouve pas la cause. Les [audits à périmètre borné](/fr/docs/audit-workflows/) donnent l’appel CLI exact.
