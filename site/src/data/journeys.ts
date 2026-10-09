import { getSiteLinks, type Locale } from './content'

export const profileIds = ['owner', 'expert', 'content', 'developer'] as const
export type ProfileId = typeof profileIds[number]
const slugs = {
  en: ['site-owners', 'seo-experts', 'content-teams', 'developers'],
  fr: ['proprietaires', 'experts-seo', 'equipes-contenu', 'developpeurs'],
}
export function profilePath(locale: Locale, id: ProfileId) {
  return `${locale === 'fr' ? '/fr/pour/' : '/for/'}${slugs[locale][profileIds.indexOf(id)]}/`
}

const tools = {
  owner: ['get_performance_overview', 'quick_wins', 'page_technical_audit'],
  expert: ['search_change_breakdown', 'search_weekday_reference', 'sitemap_audit', 'link_targets_audit', 'seo_change_impact'],
  content: ['content_brief', 'heading_audit', 'editorial_audit', 'rewrite_fidelity_check'],
  developer: ['get_capabilities', 'page_technical_audit', 'schema_validate', 'hreflang_audit', 'crawl_import_preview'],
} satisfies Record<ProfileId, string[]>

const copy = {
  fr: [
    {
      label: 'Propriétaire de site', title: 'Sachez quoi corriger sur votre site.',
      intro: 'Obtenez un premier état des lieux, des explications sur vos chiffres et trois actions à examiner en priorité.',
      question: 'Quelles sont les trois corrections prioritaires sur mon site ?',
      checks: ['Clics, impressions et pages visibles dans Google.', 'Pages proches de la première page et titres peu cliqués.', 'Métadonnées et problèmes techniques sur un échantillon de pages.'],
      result: 'Pour chaque action : la page concernée, la preuve, le changement proposé et la mesure à suivre.',
      boundary: 'Une opportunité détectée ne garantit pas un gain de classement. Vous choisissez les corrections à appliquer.',
      guide: 'examples/quick-audit/',
      request: 'Mon site : https://example.com (à remplacer). Fais un premier audit borné : 28 jours de données Google si accessibles et au maximum trois pages publiques. Explique les chiffres en langage courant. Propose trois actions avec les URL, preuves et métriques à suivre. Si les données privées manquent, propose les contrôles publics disponibles et précise la limite.',
    },
    {
      label: 'Expert SEO / agence', title: 'Passez du signal à un diagnostic vérifiable.',
      intro: 'Examinez les variations par dimension, les fenêtres comparables et les contrôles de pages avec leurs sources et leur couverture.',
      question: 'Quelles pages et requêtes contribuent à cette baisse, et quelles preuves justifient les actions ?',
      checks: ['Contributions par page, requête, pays ou appareil sur deux périodes Google égales.', 'Référence de mêmes jours de semaine et suivi d’un changement déclaré.', 'Sitemaps, liens internes et destinations HTTP avec périmètre d’échantillonnage.'],
      result: 'Un diagnostic avec périodes effectives, identifiants de sources, couverture, limites et contrôles à rejouer.',
      boundary: 'Bing ne fournit pas les mêmes garanties de fenêtre que Google. Une variation après un changement ne prouve pas sa causalité.',
      guide: 'audit-workflows/',
      request: 'Mon site : https://example.com (à remplacer). Demande les deux périodes Google égales et disjointes à comparer, les dimensions utiles et un budget de requêtes avant de lancer search_change_breakdown. Sépare contributions par dimension, constats et hypothèses. Pour chaque résultat, conserve _meta, les identifiants des sources, les dates demandées et effectives, la couverture et les données indisponibles. Propose les contrôles de pages qui permettraient de vérifier les hypothèses. Ajoute Bing seulement si ses données sont comparables et accessibles ; sinon, présente ses résultats séparément.',
    },
    {
      label: 'Équipe contenu', title: 'Préparez et révisez vos contenus avec leurs sources.',
      intro: 'Utilisez les requêtes observées pour préparer un brief, puis relisez un brouillon ou une réécriture avec des contrôles explicites.',
      question: 'Que faut-il revoir dans ce contenu, et quels faits doit-on conserver ?',
      checks: ['Requêtes et pages observées pour un brief, si GSC et GA4 sont configurés.', 'Titres et sous-titres d’une page publique.', 'Règles éditoriales FR/EN et changements de nombres ou de formulations protégées.'],
      result: 'Un brief fondé sur les données disponibles ou une liste de passages à relire, avec leurs extraits et limites.',
      boundary: 'Les alertes éditoriales ne détectent pas l’auteur IA. La comparaison mécanique ne certifie ni la vérité ni la fidélité du sens.',
      guide: 'editorial-workflows/',
      request: 'Demande-moi le brouillon à examiner, sa langue (fr ou en) et son format (plain ou markdown). Lance editorial_audit sur le texte fourni, sans appel à Google ni Bing. Présente les passages à relire, les règles déclenchées et leurs limites. Si je fournis aussi une version réécrite, utilise rewrite_fidelity_check pour comparer les éléments protégés. Conserve faits, chiffres, dates, citations, modalités et causalité. Les contrôles mécaniques ne certifient pas la fidélité sémantique. Ne réécris et ne publie rien sans demande.',
    },
    {
      label: 'Développeur', title: 'Intégrez les contrôles SEO à vos workflows.',
      intro: 'Utilisez MCP ou la CLI, vérifiez les réponses JSON et choisissez les familles d’outils utiles à votre intégration.',
      question: 'Quels contrôles puis-je appeler et comment interpréter leurs réponses ?',
      checks: ['Outils exposés par le serveur, paramètres et réponses JSON.', 'Canonical, robots, hreflang et données structurées sur des pages publiques.', 'Aperçu d’un export SiteOne JSON fourni, sans lancement de crawl.'],
      result: 'Des appels reproductibles, les résultats observés et les limites à traiter dans votre intégration.',
      boundary: 'L’exposition d’un outil ne prouve pas l’accès aux API. La sélection de familles ne donne aucun droit d’écriture.',
      guide: 'architecture/',
      request: 'Utilise get_capabilities pour inventorier les outils réellement exposés dans ce serveur. Explique les familles configurées, les paramètres d’entrée et le rôle de _meta. Guide-moi pour tester les contrôles sans identifiants privés, puis demande les URL publiques ou un export SiteOne JSON fourni avant les appels concernés. Distingue données observées, calculs, heuristiques et indisponibilité. N’accède à aucun fichier local, ne stocke aucun résultat et n’effectue aucune écriture externe.',
    },
  ],
  en: [
    {
      label: 'Site owner', title: 'Know what to fix on your site.',
      intro: 'Get a first assessment, plain-language explanations of your metrics and three actions to review first.',
      question: 'Which three fixes should I prioritize on my site?',
      checks: ['Google clicks, impressions and visible pages.', 'Pages close to page one and snippets with few clicks.', 'Metadata and technical issues on a sample of pages.'],
      result: 'For each action: the affected page, evidence, suggested change and metric to track.',
      boundary: 'A detected opportunity does not guarantee higher rankings. You choose which changes to apply.',
      guide: 'examples/quick-audit/',
      request: 'My site: https://example.com (replace it). Run a bounded first audit: 28 days of Google data if accessible and at most three public pages. Explain the metrics in plain language. Suggest three actions with URLs, evidence and metrics to track. If private data is missing, propose available public checks and state the limitation.',
    },
    {
      label: 'SEO expert / agency', title: 'Turn a signal into a verifiable diagnosis.',
      intro: 'Investigate dimensional contributions, comparable windows and page checks with their source identifiers and coverage.',
      question: 'Which pages and queries contribute to this drop, and what evidence supports the actions?',
      checks: ['Page, query, country or device contributions across two equal Google periods.', 'Same-weekday references and follow-up of a declared change.', 'Sitemaps, internal links and HTTP destinations with sampling boundaries.'],
      result: 'A diagnosis with effective periods, source identifiers, coverage, limits and checks to rerun.',
      boundary: 'Bing does not provide the same window guarantees as Google. A change followed by a variation does not establish causality.',
      guide: 'audit-workflows/',
      request: 'My site: https://example.com (replace it). Ask for two equal, disjoint Google periods, the relevant dimensions and a request budget before running search_change_breakdown. Separate contributions by dimension, observations and hypotheses. Preserve _meta, source identifiers, requested and effective dates, coverage and unavailable data beside each result. Propose page checks to investigate the hypotheses. Add Bing only if its data is comparable and accessible; otherwise report it separately.',
    },
    {
      label: 'Content team', title: 'Plan and review content with its sources.',
      intro: 'Use observed queries to prepare a brief, then review a draft or rewrite with explicit checks.',
      question: 'What needs review in this content, and which facts must be preserved?',
      checks: ['Observed queries and pages for a brief, when GSC and GA4 are configured.', 'Titles and headings on a public page.', 'FR/EN editorial rules and changes to numbers or protected qualifiers.'],
      result: 'A brief based on available data or passages to review, with excerpts and limits.',
      boundary: 'Editorial warnings do not detect AI authorship. Mechanical comparisons certify neither truth nor preservation of meaning.',
      guide: 'editorial-workflows/',
      request: 'Ask me for the draft, its language (fr or en) and format (plain or markdown). Run editorial_audit on the supplied text without calling Google or Bing. Report passages to review, triggered rules and limits. If I also supply a rewrite, use rewrite_fidelity_check to compare protected elements. Preserve facts, numbers, dates, quotes, modality and causality. Mechanical checks do not certify semantic fidelity. Do not rewrite or publish anything unless requested.',
    },
    {
      label: 'Developer', title: 'Integrate SEO checks into your workflows.',
      intro: 'Use MCP or the CLI, inspect JSON responses and choose tool families for your integration.',
      question: 'Which checks can I call and how should I interpret their responses?',
      checks: ['Tools exposed by this server, parameters and JSON responses.', 'Canonical, robots, hreflang and structured data on public pages.', 'Preview of caller-supplied SiteOne JSON, without starting a crawl.'],
      result: 'Reproducible calls, observed results and boundaries to handle in your integration.',
      boundary: 'Tool discovery does not prove API access. Family selection grants no write permissions.',
      guide: 'architecture/',
      request: 'Use get_capabilities to inventory tools actually exposed by this server. Explain configured families, input parameters and the role of _meta. Guide me through checks without private credentials, then ask for public URLs or caller-supplied SiteOne JSON before the relevant calls. Separate observations, calculations, heuristics and unavailable data. Do not access local files, store results or perform external writes.',
    },
  ],
}

export function getProfiles(locale: Locale) {
  return profileIds.map((id, index) => ({ id, ...copy[locale][index], tools: tools[id], href: profilePath(locale, id) }))
}
export function getProfilePrompt(locale: Locale, request: string) {
  const source = `${getSiteLinks(locale).repository}/blob/main/docs/installation.md`
  const setup = locale === 'fr'
    ? `Utilise Search Console MCP (gsc-mcp-tools). Si ses outils ne sont pas disponibles, demande quel client MCP j’utilise et guide-moi avec ${source}. Attends la connexion avant l’analyse. get_capabilities indique les outils exposés, pas les accès aux sources. Pour les données Google, vérifie la propriété avec list_properties. Pour Bing, utilise bing_sites_list si nécessaire. Configure uniquement les sources utiles, sans demander de secrets dans la conversation. Demande les informations manquantes et signale les outils indisponibles. Conserve _meta et les limites des résultats. Ne modifie pas le site et ne soumets aucune URL.`
    : `Use Search Console MCP (gsc-mcp-tools). If its tools are unavailable, ask which MCP client I use and guide me with ${source}. Wait for the connection before analysis. get_capabilities reports exposed tools, not source access. For Google data, verify the property with list_properties. For Bing, use bing_sites_list when needed. Configure only required sources and do not ask for secrets in this conversation. Ask for missing inputs and report unavailable tools. Preserve _meta and result boundaries. Do not change the site or submit URLs.`
  return `${setup}\n\n${request}`
}
