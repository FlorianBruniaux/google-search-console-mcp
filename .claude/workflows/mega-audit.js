/**
 * mega-audit - Audit exhaustif multi-agents d'un site GSC
 *
 * Usage :
 *   Workflow({ name: "mega-audit", args: { siteUrl: "sc-domain:example.com" } })
 *   Workflow({ name: "mega-audit", args: { siteUrl: "https://www.example.com/" } })
 *
 * Durée estimée : 8-15 minutes (25+ agents en parallèle)
 * Coût estimé   : ~$2-5 selon la taille du site (agents haiku/sonnet + 1 Opus final)
 *
 * Prérequis :
 *   - Accès GSC configuré (OAuth token.json ou GSC_CREDENTIALS_PATH)
 *   - Chrome DevTools MCP actif (pour Lighthouse + screenshots)
 *   - Claude-in-Chrome MCP actif (pour navigation réelle)
 *   - Perplexity MCP actif (pour benchmarks externes)
 *
 * Output : rapport Markdown P0/P1/P2 retourné par le Workflow
 */

export const meta = {
  name: 'mega-audit',
  description: 'Audit exhaustif multi-agents d\'un site GSC (SEO, tech, UX, sécurité)',
  phases: [
    { title: 'Discovery', detail: 'Vérification accès GSC et récupération des URLs top' },
    { title: 'SEO Performance', detail: 'Traffic, anomalies, AI Overviews, périodes' },
    { title: 'Technical SEO', detail: 'Indexing, sitemaps, schema markup' },
    { title: 'Content & Keywords', detail: 'Cannibalization, striking distance, quick wins' },
    { title: 'Page Analysis', detail: 'Pipeline top 10 pages , health score + CRuX + queries' },
    { title: 'Frontend & UX', detail: 'Lighthouse, performance trace, UX review' },
    { title: 'Security & Research', detail: 'Audit sécurité + benchmarks externes' },
    { title: 'Synthesis', detail: 'Rapport final P0/P1/P2 par agent Opus' },
  ],
}

// Guard: siteUrl obligatoire
if (!args || !args.siteUrl) {
  throw new Error('mega-audit requires args.siteUrl, e.g. Workflow({name: "mega-audit", args: {siteUrl: "sc-domain:example.com"}})')
}

const SITE_URL = args.siteUrl
log(`Démarrage audit complet pour : ${SITE_URL}`)

// ─── PHASE 0 : DISCOVERY ────────────────────────────────────────────────────
phase('Discovery')

const discoveryData = await agent(
  `Tu dois réaliser la phase Discovery de l'audit pour le site "${SITE_URL}".

  Exécute dans l'ordre :
  1. mcp__gsc-mcp__list_properties , confirme que "${SITE_URL}" est accessible
  2. mcp__gsc-mcp__get_site_details avec siteUrl="${SITE_URL}"
  3. mcp__gsc-mcp__check_alerts avec siteUrl="${SITE_URL}"
  4. mcp__gsc-mcp__get_performance_overview avec siteUrl="${SITE_URL}", days=90
  5. mcp__gsc-mcp__get_search_analytics avec siteUrl="${SITE_URL}", days=28, limit=20, dimensions=["page"]
     → extraire les 20 URLs les plus performantes (par clicks)

  Retourne un JSON structuré :
  {
    "siteUrl": "${SITE_URL}",
    "isAccessible": true|false,
    "siteDetails": { ... },
    "alerts": [ ... ],
    "overview": { clicks, impressions, ctr, position, period },
    "topUrls": ["url1", "url2", ..., "url20"]
  }`,
  {
    label: 'discovery',
    phase: 'Discovery',
    model: 'sonnet',
    schema: {
      type: 'object',
      required: ['siteUrl', 'isAccessible', 'topUrls'],
      properties: {
        siteUrl: { type: 'string' },
        isAccessible: { type: 'boolean' },
        siteDetails: { type: 'object' },
        alerts: { type: 'array' },
        overview: { type: 'object' },
        topUrls: { type: 'array', items: { type: 'string' } },
      },
    },
  }
)

if (!discoveryData || !discoveryData.isAccessible) {
  throw new Error(`Site "${SITE_URL}" non accessible dans GSC. Vérifie la propriété et les droits.`)
}

log(`Discovery OK , ${discoveryData.topUrls.length} URLs top identifiées`)
const TOP_URLS = discoveryData.topUrls.slice(0, 10)

// ─── PHASES 1, 2, 3 : SEO PARALLÈLE ────────────────────────────────────────
const [perfResults, techResults, contentResults] = await parallel([

  // ── Phase 1 : SEO Performance & Traffic ──────────────────────────────────
  () => parallel([
    () => agent(
      `Agent gsc-seo-reporter : génère le rapport SEO complet pour "${SITE_URL}".
       Utilise tous les outils à disposition : get_performance_overview (90j),
       traffic_health_check, analytics_anomalies, compare_search_periods (28j vs 28j prior),
       search_type_breakdown. Retourne un résumé structuré des métriques clés et des tendances.`,
      { label: 'seo-reporter', phase: 'SEO Performance', model: 'sonnet', agentType: 'gsc-seo-reporter' }
    ),
    () => agent(
      `Agent gsc-traffic-doctor : diagnostique les drops de trafic pour "${SITE_URL}".
       Utilise : traffic_drops, check_alerts, analytics_anomalies, seo_lost_queries,
       compare_search_periods. Identifie les dates de chute, requêtes perdues, et cause probable.`,
      { label: 'traffic-doctor', phase: 'SEO Performance', model: 'sonnet', agentType: 'gsc-traffic-doctor' }
    ),
    () => agent(
      `Agent gsc-ai-overviews-analyst : mesure l'impact des AI Overviews sur le CTR pour "${SITE_URL}".
       Utilise : ai_overviews_impact, compare_search_periods.
       Quantifie la cannibalisation CTR et identifie les pages les plus touchées.`,
      { label: 'ai-overviews', phase: 'SEO Performance', model: 'sonnet', agentType: 'gsc-ai-overviews-analyst' }
    ),
  ]),

  // ── Phase 2 : Technical SEO ───────────────────────────────────────────────
  () => parallel([
    () => agent(
      `Agent gsc-indexing-auditor : audit complet de l'indexation pour "${SITE_URL}".
       Utilise : check_indexing_issues, get_search_analytics (pages),
       batch_url_inspection sur les 10 URLs les plus importantes : ${JSON.stringify(TOP_URLS)}.
       Identifie les pages non indexées, erreurs de crawl, et problèmes de couverture.`,
      { label: 'indexing-audit', phase: 'Technical SEO', model: 'sonnet', agentType: 'gsc-indexing-auditor' }
    ),
    () => agent(
      `Agent gsc-sitemap-auditor : audit des sitemaps pour "${SITE_URL}".
       Utilise : list_sitemaps, sitemap_audit, check_indexing_issues.
       Retourne le ratio soumis/indexés, les erreurs, et les recommandations.`,
      { label: 'sitemap-audit', phase: 'Technical SEO', model: 'sonnet', agentType: 'gsc-sitemap-auditor' }
    ),
    () => agent(
      `Agent gsc-schema-auditor : audit des données structurées pour "${SITE_URL}".
       Utilise : get_search_analytics (top 20 pages), schema_validate sur chaque URL.
       Identifie les erreurs JSON-LD bloquant les rich results et leur impact potentiel.`,
      { label: 'schema-audit', phase: 'Technical SEO', model: 'sonnet', agentType: 'gsc-schema-auditor' }
    ),
  ]),

  // ── Phase 3 : Content & Keywords ──────────────────────────────────────────
  () => parallel([
    () => agent(
      `Agent gsc-cannibalization-checker : détecte la cannibalisation de mots-clés pour "${SITE_URL}".
       Utilise : seo_cannibalization, get_advanced_search_analytics.
       Retourne les requêtes où 2+ pages se cannibalisent, avec impact estimé.`,
      { label: 'cannibalization', phase: 'Content & Keywords', model: 'sonnet', agentType: 'gsc-cannibalization-checker' }
    ),
    () => agent(
      `Analyse les opportunités de contenu rapides pour "${SITE_URL}".
       Utilise ces outils MCP dans l'ordre :
       1. mcp__gsc-mcp__quick_wins avec siteUrl="${SITE_URL}"
       2. mcp__gsc-mcp__seo_striking_distance avec siteUrl="${SITE_URL}"
       3. mcp__gsc-mcp__seo_lost_queries avec siteUrl="${SITE_URL}"
       4. mcp__gsc-mcp__discover_performance avec siteUrl="${SITE_URL}"

       Retourne : { quickWins: [...], strikingDistance: [...], lostQueries: [...] }
       Chaque item doit avoir : query, currentPosition, estimatedImpact, action.`,
      { label: 'content-opportunities', phase: 'Content & Keywords', model: 'haiku' }
    ),
    () => agent(
      `Récupère les données analytics avancées et crée des content briefs pour "${SITE_URL}".
       1. mcp__gsc-mcp__get_advanced_search_analytics avec siteUrl="${SITE_URL}", days=90
       2. mcp__gsc-mcp__content_brief pour les 3 meilleures opportunités identifiées
       3. mcp__gsc-mcp__search_type_breakdown avec siteUrl="${SITE_URL}"
          (breakdown web/image/video/news)

       Retourne un résumé des insights de distribution et des briefs.`,
      { label: 'content-briefs', phase: 'Content & Keywords', model: 'haiku' }
    ),
  ]),

])

// ─── PHASE 4 : PAGE-LEVEL ANALYSIS (pipeline) ───────────────────────────────
phase('Page Analysis')
log(`Analyse page par page sur ${TOP_URLS.length} URLs...`)

const pageResults = await pipeline(
  TOP_URLS,
  // Stage 1 : health score + CRuX + inspection , haiku suffit (mécanique)
  (url, _, idx) => agent(
    `Analyse technique de la page #${idx + 1} : "${url}" pour le site "${SITE_URL}".
     Exécute dans l'ordre :
     1. mcp__gsc-mcp__page_health_score avec siteUrl="${SITE_URL}", pageUrl="${url}"
     2. mcp__gsc-mcp__crux_page_vitals avec pageUrl="${url}"
     3. mcp__gsc-mcp__inspect_url avec siteUrl="${SITE_URL}", inspectionUrl="${url}"
     4. mcp__gsc-mcp__get_search_by_page_query avec siteUrl="${SITE_URL}", pageUrl="${url}", days=28

     Retourne : { url, healthScore, cwv: {lcp, fid, cls, inp}, isIndexed, topQueries: [] }`,
    {
      label: `page-${idx + 1}`,
      phase: 'Page Analysis',
      model: 'haiku',
      schema: {
        type: 'object',
        required: ['url', 'isIndexed', 'healthScore'],
        properties: {
          url: { type: 'string' },
          healthScore: { type: 'number' },
          cwv: { type: 'object' },
          isIndexed: { type: 'boolean' },
          topQueries: { type: 'array' },
        },
      },
    }
  ),
  // Stage 2 : analyse approfondie si score < 70 ou page non indexée
  (pageData, url, idx) => {
    if (!pageData) return null
    if (pageData.healthScore >= 70 && pageData.isIndexed) return pageData
    return agent(
      `Deep dive sur la page "${url}" qui a un health score faible (${pageData.healthScore ?? 'N/A'})
       ou problème d'indexation (isIndexed: ${pageData.isIndexed}).
       Utilise mcp__gsc-mcp__page_analysis avec siteUrl="${SITE_URL}", pageUrl="${url}".
       Identifie les causes précises et propose 2-3 actions correctives avec priorité.`,
      {
        label: `page-deepdive-${idx + 1}`,
        phase: 'Page Analysis',
        model: 'sonnet',
        agentType: 'gsc-page-analyst',
      }
    ).then(deepDive => ({ ...pageData, deepDive }))
  }
)

log(`Page analysis terminée , ${pageResults.filter(Boolean).length}/${TOP_URLS.length} pages analysées`)

// ─── PHASES 5 & 6 : FRONTEND/UX + SÉCURITÉ/RECHERCHE ───────────────────────
const HOMEPAGE = TOP_URLS[0] || SITE_URL

const [frontendResults, securityResearchResults] = await parallel([

  // ── Phase 5 : Frontend / UX / Performance ────────────────────────────────
  () => parallel([
    () => agent(
      `Tu es un expert frontend. Analyse les performances et la qualité du code frontend
       du site "${SITE_URL}" (homepage : "${HOMEPAGE}").

       1. Lance mcp__chrome-devtools__new_page pour ouvrir la homepage
       2. Lance mcp__chrome-devtools__lighthouse_audit sur "${HOMEPAGE}" avec categories:
          ["performance","accessibility","best-practices","seo"]
       3. Lance mcp__chrome-devtools__take_screenshot pour capturer l'état visuel
       4. Analyse les résultats Lighthouse et identifie les 5 problèmes les plus impactants

       Retourne : { lighthouseScores: {perf, a11y, bestPractices, seo},
                    topIssues: [{category, issue, impact, fix}] }`,
      { label: 'lighthouse', phase: 'Frontend & UX', model: 'sonnet' }
    ),
    () => agent(
      `Analyse UX et accessibilité du site "${SITE_URL}".

       Évalue depuis la description visuelle et les métriques disponibles :
       - Navigation et structure de l'information
       - Accessibilité WCAG 2.1 AA
       - Cohérence du design system
       - Mobile-first et responsive design
       - Core Web Vitals UX impact

       Base ton analyse sur les données CRuX déjà collectées et les screenshots disponibles.
       Retourne 5 recommandations UX prioritaires avec niveau d'effort (low/medium/high).`,
      { label: 'ux-review', phase: 'Frontend & UX', model: 'sonnet', agentType: 'ui-designer' }
    ),
    () => agent(
      `Analyse performance avancée du site "${HOMEPAGE}".

       1. mcp__chrome-devtools__new_page → ouvrir la page
       2. mcp__chrome-devtools__performance_start_trace
       3. mcp__chrome-devtools__navigate_page vers "${HOMEPAGE}"
       4. mcp__chrome-devtools__performance_stop_trace
       5. mcp__chrome-devtools__performance_analyze_insight

       Identifie les goulots d'étranglement (JS blocking, render-blocking resources,
       LCP candidates, CLS causes). Retourne top 3 quick wins performance.`,
      { label: 'perf-trace', phase: 'Frontend & UX', model: 'sonnet' }
    ),
  ]),

  // ── Phase 6 : Sécurité + Recherche externe ───────────────────────────────
  () => parallel([
    () => agent(
      `Audit de sécurité du site "${SITE_URL}" (homepage : "${HOMEPAGE}").

       Points à vérifier :
       1. Headers de sécurité manquants (CSP, HSTS, X-Frame-Options, etc.)
          → utilise mcp__chrome-devtools__get_network_request pour inspecter les headers
       2. Ressources chargées en HTTP non sécurisé (mixed content)
       3. Cookies sans flags Secure/HttpOnly/SameSite
       4. Exposition d'informations sensibles dans les sources

       Retourne : { criticalIssues: [], warnings: [], passed: [] }
       Chaque issue : { category, description, severity: "critical|high|medium|low", fix }`,
      { label: 'security-audit', phase: 'Security & Research', model: 'sonnet' }
    ),
    () => agent(
      `Recherche externe et benchmarks pour le site "${SITE_URL}".

       1. mcp__perplexity__perplexity_search : cherche les 3 concurrents principaux
          du site (déduis la niche depuis l'URL) et leurs métriques SEO estimées
       2. mcp__perplexity__perplexity_research : benchmarks industrie pour la niche
          (CTR moyen, positions moyennes, Core Web Vitals secteur)

       Retourne : {
         competitors: [{name, estimatedTraffic, strengths}],
         industryBenchmarks: { avgCTR, avgPosition, cwvP75 }
       }`,
      { label: 'external-research', phase: 'Security & Research', model: 'sonnet' }
    ),
    () => agent(
      `Opportunités GEO (Generative Engine Optimization) pour "${SITE_URL}".

       Analyse :
       - Présence potentielle dans AI Overviews Google
       - Optimisation pour ChatGPT/Perplexity/Gemini
       - Schémas de données structurées manquants pour l'IA
       - Score de confiance E-E-A-T estimé

       Utilise mcp__gsc-mcp__crux_history avec siteUrl="${SITE_URL}" pour la tendance long terme.
       Utilise mcp__gsc-mcp__news_performance avec siteUrl="${SITE_URL}" si applicable.

       Retourne 3 recommandations GEO avec impact estimé.`,
      { label: 'geo-opportunities', phase: 'Security & Research', model: 'haiku' }
    ),
  ]),

])

// ─── PHASE 7 : SYNTHÈSE FINALE ───────────────────────────────────────────────
phase('Synthesis')
log('Synthèse de tous les résultats par agent Opus...')

const auditSummary = {
  siteUrl: SITE_URL,
  overview: discoveryData.overview,
  alerts: discoveryData.alerts,
  seoPerformance: perfResults,
  technicalSEO: techResults,
  contentKeywords: contentResults,
  pageAnalysis: pageResults.filter(Boolean),
  frontendUX: frontendResults,
  securityResearch: securityResearchResults,
}

const finalReport = await agent(
  `Tu es l'auditeur en chef. Tu viens de recevoir les résultats d'un audit complet du site "${SITE_URL}"
   réalisé par 20+ agents spécialisés. Synthétise tout ça en un rapport d'audit actionnable.

   DONNÉES D'AUDIT :
   ${JSON.stringify(auditSummary, null, 2)}

   STRUCTURE OBLIGATOIRE DU RAPPORT (en français, format Markdown) :

   # Audit Complet , ${SITE_URL}
   *Généré le [date], basé sur les données des 90 derniers jours*

   ## Synthèse exécutive (5 lignes max)
   [Bilan cash : ce qui va, ce qui ne va pas, tendance générale]

   ## Métriques clés
   | Métrique | Valeur | Tendance |
   [tableau avec clicks, impressions, CTR, position moyenne, pages indexées]

   ## P0 , Blockers critiques (à corriger cette semaine)
   [Max 3 items. Chacun : problème précis + impact mesuré + action exacte + effort]

   ## P1 , Priorité haute (à planifier ce mois)
   [Max 5 items. Même format.]

   ## P2 , Opportunités (backlog trimestriel)
   [Max 7 items. Même format.]

   ## Quick Wins immédiats
   [3 actions que l'équipe peut faire en moins d'1h chacune]

   ## Points positifs
   [Ce qui fonctionne bien , pour ne pas casser ce qui marche]

   ## Prochaines étapes recommandées
   [Timeline réaliste sur 4 semaines]

   RÈGLES :
   - Nommer des URLs, requêtes, et valeurs précises , pas de généralités
   - Varier les longueurs de phrases
   - Pas d'em dash, pas de buzzwords vides
   - Finir naturellement, pas en slogan`,
  {
    label: 'synthesis-opus',
    phase: 'Synthesis',
    model: 'opus',
  }
)

log('Audit terminé.')
return finalReport
