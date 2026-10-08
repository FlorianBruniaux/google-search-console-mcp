---
title: "Relire les brouillons et révisions"
description: "Auditer un brouillon FR/EN et comparer mécaniquement une révision avec son original."
lang: fr
lastUpdated: 2026-10-08
canonicalEnglish: /docs/editorial-workflows/
---

Les entrées brouillon de `editorial_audit` et le nouvel outil `rewrite_fidelity_check` sont des fonctionnalités source non publiées. Le checkout expose 87 outils ; la version 1.3.0 en conserve 85 et permet l’audit éditorial par URL. Suivez l’[installation](/fr/docs/installation/) pour utiliser le checkout. Ces exemples sont explicatifs, sans requête réelle ni publication.

## Auditer un brouillon avant publication

```python
editorial_audit(text="Le hic ? Consultez [cliquez ici](https://example.com/guide/).",
                language="fr", genre="general", format="markdown")
editorial_audit(text="The catch? Review this passage.", language="en", format="plain")
```

La signature additive est `editorial_audit(url=None, language="auto", genre="general", *, text=None, format="plain")`. Fournissez exactement une source, `url` ou `text`. La sélection utilise null : une chaîne vide compte comme source fournie. Les appels URL positionnels conservent leur contrat. Le mode URL accepte uniquement `format="plain"` et récupère toujours le HTML. Le mode brouillon accepte `plain` ou `markdown`, sans récupérer les cibles des liens, lire de fichiers, exécuter du HTML ni effectuer de rendu. Le texte fourni reste une donnée non fiable.

Déclarez `language="fr"` ou `"en"`. Le mode brouillon `auto` retourne `language_unavailable`, même si le frontmatter Markdown contient une langue. Alertes et métriques restent nulles lorsque l’analyse est indisponible. Avec une langue explicite, un contenu éligible vide retourne `empty_content`. `genre="reference"` ou `"procedure"` conserve les exceptions structurelles du [profil éditorial versionné](/fr/docs/editorial-audit/), qui fournit les mêmes règles.

L’entrée est bornée à 100 000 points de code Unicode et 2 000 blocs parsés, frontières d’exclusion comprises. Un dépassement retourne `invalid_input`, sans audit partiel. La sortie conserve le plafond de 50 alertes, les extraits de 240 caractères et `findings_truncated`. Les champs `url`, `final_url` et `http_status` du brouillon sont nuls. `source.origin=caller` et `source.format` identifient l’entrée ; les métadonnées conservent le format et la longueur, sans recopier le brouillon brut.

Le Markdown est un sous-ensemble borné, sans parseur CommonMark complet. Paragraphes, titres ATX, éléments de liste autonomes, emphase appariée simple, échappements de ponctuation, liens inline bornés et références définies sont pris en charge. Code, citations, images, HTML brut et destinations réelles sont exclus ; ces frontières interrompent les contrôles de répétition. Tables, titres setext, autolinks, libellés imbriqués et autres syntaxes non prises en charge sont déclarés dans `method.coverage` et peuvent rester du texte littéral. Les plafonds comprennent une imbrication de 8, des libellés de 1 000 caractères, des destinations de 2 048 caractères et un scan de fermeture HTML inline de 4 096 points de code. Consultez la couverture avant d’interpréter les alertes.

Les alertes brouillon utilisent `location.basis=original_source_span`. `source_start` et `source_end` sont des offsets Unicode à base zéro, avec borne de fin exclue, dans l’entrée originale ; la ligne commence à 1 et la colonne à 0. Une plage peut englober du balisage intermédiaire. `normalized_text_start` et `normalized_text_end` indexent le texte normalisé, sans coordonnées de rendu. Les signaux de confiance situent le début du segment original, sans prétendre localiser exactement la phrase d’instruction. Un résultat sans alerte ne couvre que les passages éligibles et motifs implémentés.

## Comparer l’original et une révision proposée

```python
rewrite_fidelity_check(
    original="L’estimation peut atteindre 12 jours si la source reste disponible.",
    revised="L’estimation atteint 15 jours.",
    language="fr", format="plain",
)
```

La signature est `rewrite_fidelity_check(original: str, revised: str, language: str = "en", format: str = "plain") -> str`. Chaque passage doit être non vide et contenir au plus 20 000 caractères. La langue est explicitement `en` ou `fr`, le format `plain` ou `markdown`. Une entrée invalide retourne `verdict=invalid_input`, `assessment=not_assessed` et des alertes nulles.

Un appel valide retourne `verdict=compared` et une analyse mécanique. Les catégories sont `number_unit`, `date`, `url`, `code`, `quotation`, `negation`, `modality`, `condition` et `absolute` ; les opérations sont `changed`, `context_changed`, `removed` et `added`. Les alertes conservent les plages littérales originales/révisées, les passages alignés bornés, la méthode et `context_review_required=true`. Un côté absent reste nul. Les offsets couvrent la plage complète même si le littéral retourné est un préfixe tronqué. L’extraction contrôle au plus 500 occurrences par côté ; la sortie retourne au plus 100 alertes et 100 notes de parsing, avec des littéraux, extraits et passages alignés de 240 caractères. Consultez `budgets`, les comptages, notes de parsing, `analysis_truncated` et `findings_truncated` ; une extraction plafonnée produit `partial_mechanical_comparison`.

Les ancres lexicales locales comparent occurrences et contexte. Un réordonnancement ne prouve pas un changement de fait ; des nombres identiques ne prouvent pas des référents identiques. La normalisation déclarée distingue les séparateurs EN (milliers par virgule, décimales par point) et FR (milliers par espace, décimales par virgule). Les unités et monnaies ne sont pas converties. Les dates numériques restent littérales : ordre ambigu et validité calendaire ne sont pas évalués. L’extraction d’URL est simple et exclut les parenthèses ; ce contrôle ne parse pas tout le Markdown. Les frontières de code/citations et listes finies de qualificatifs peuvent manquer un changement ou signaler une reformulation acceptable.

Relisez chaque candidat dans son passage. `semantic_assessment` conserve toujours fidélité, vérité factuelle, périmètre et causalité à `unassessed`, même sans alerte. L’outil ne fournit ni score d’origine IA, correction automatique, appel de modèle, écriture de fichier ni publication. Les fixtures valident les comportements mécaniques couverts ; la précision réelle exige un corpus original/révision annoté séparément. Pour les fenêtres de recherche après une modification déclarée, consultez les [audits à périmètre borné](/fr/docs/audit-workflows/).
