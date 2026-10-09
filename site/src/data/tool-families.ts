import type { Locale } from './content'

// Descriptions explain the family boundary; individual contracts come from Python.
const families = {
  core: ['Access and discovery', 'Accès et découverte', 'Discover tools and source properties.', 'Lister les outils et les propriétés accessibles.', 'installation/'],
  analytics: ['Search performance', 'Performances de recherche', 'Google metrics, equal-period contributions and same-weekday references.', 'Métriques Google, contributions sur périodes égales et références de mêmes jours de semaine.', 'audit-workflows/'],
  seo: ['Opportunities and changes', 'Opportunités et changements', 'Opportunity candidates, traffic drops and declared-change follow-up. Heuristic diagnoses need review.', 'Opportunités candidates, baisses de trafic et suivi de changements déclarés. Les diagnostics heuristiques demandent une revue.', 'audit-workflows/'],
  inspection: ['Google indexing', 'Indexation Google', 'Google URL Inspection on a bounded sample. Search traffic alone does not prove indexing state.', 'URL Inspection Google sur un échantillon borné. Le trafic seul ne démontre pas l’état d’indexation.', 'examples/indexing-issues/'],
  indexing: ['URL submissions', 'Soumissions d’URL', 'Eligible Google Indexing API and IndexNow submissions. Acceptance proves neither crawling nor indexing.', 'Soumissions éligibles via Google Indexing API et IndexNow. Une acceptation ne prouve ni exploration ni indexation.', 'evidence-and-safety/'],
  sitemaps: ['Sitemaps', 'Sitemaps', 'Submitted sitemap status and declared URLs compared with search visibility.', 'Statut des sitemaps soumis et comparaison des URL déclarées avec la visibilité en recherche.', 'examples/full-audit/'],
  ga4: ['GA4 behavior', 'Comportements GA4', 'Sessions, engagement, events and AI referrers, when the GA4 property is configured.', 'Sessions, engagement, événements et référents IA, si la propriété GA4 est configurée.', 'google-setup/'],
  cross: ['Source comparisons', 'Comparaisons entre sources', 'GSC and GA4 reports or Google and Bing comparisons, with source and window guards.', 'Rapports GSC et GA4 ou comparaisons Google et Bing, avec contrôle des sources et des fenêtres.', 'evidence-and-safety/'],
  crux: ['Field performance', 'Performances terrain', 'CrUX Core Web Vitals where sufficient field data exists; separate API key required.', 'Core Web Vitals CrUX si les données terrain suffisent ; clé API distincte requise.', 'google-setup/'],
  technical: ['Technical checks', 'Contrôles techniques', 'Schema, crawler rules, PageSpeed and caller-supplied crawl previews, each with its own inputs.', 'Schema, règles de robots, PageSpeed et aperçus d’exports de crawl fournis, selon leurs entrées.', 'audit-workflows/'],
  drift: ['Page changes', 'Évolutions des pages', 'Capture and compare locally stored page baselines. Persistence is explicit.', 'Capturer et comparer des références de pages stockées localement. Le stockage est explicite.', 'architecture/'],
  content: ['Page content', 'Contenu des pages', 'Headings, metadata, canonical, hreflang and preload checks on fetched public HTML.', 'Titres, métadonnées, canonical, hreflang et preload sur le HTML public récupéré.', 'examples/page-deep-dive/'],
  editorial: ['Drafts and rewrites', 'Brouillons et réécritures', 'FR/EN review warnings and protected-literal comparisons. No authorship or semantic certification.', 'Alertes éditoriales FR/EN et comparaison des éléments protégés. Aucune certification d’auteur ou de sens.', 'editorial-workflows/'],
  links: ['Internal links', 'Liens internes', 'Link zones, sampled graphs and bounded HTTP destination checks; no site-wide orphan proof.', 'Zones de liens, graphes échantillonnés et contrôles HTTP bornés ; sans preuve de pages orphelines sur tout le site.', 'audit-workflows/'],
  bing: ['Bing Webmaster', 'Bing Webmaster', 'Verified sites, query/page performance, crawl signals and guarded submissions.', 'Sites vérifiés, performances par requête ou page, signaux d’exploration et soumissions encadrées.', 'bing-setup/'],
} as const

export function familyContent(family: string, locale: Locale) {
  const entry = families[family as keyof typeof families]
  if (!entry) throw new Error(`Undocumented tool family: ${family}`)
  return { label: entry[locale === 'fr' ? 1 : 0], description: entry[locale === 'fr' ? 3 : 2], guide: entry[4] }
}

export const externalWrites = new Set(['submit_url', 'submit_batch', 'sitemaps_delete', 'indexnow_submit', 'submit_sitemap', 'bing_url_submit', 'bing_urls_submit_batch', 'bing_feed_submit', 'bing_feed_remove'])
