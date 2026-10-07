import { siteLinks, type Locale } from './content'

export function getSeoPrompt(locale: Locale, route: { prompt: string; guide: string }) {
  const source = `${siteLinks.repository}/blob/main`
  const instructions = locale === 'fr'
    ? `Utilise les outils de Search Console MCP (paquet gsc-mcp-tools) pour réaliser cette analyse.

Avant de commencer, vérifie que ses outils sont disponibles dans cette conversation. Sinon, demande quel assistant j’utilise, puis guide-moi pour installer le paquet avec uv tool install gsc-mcp-tools, déclarer son exécutable dans mon client MCP et redémarrer ou reconnecter le client. Suis ce guide :
${source}/docs/installation.md
Attends que la connexion soit vérifiée avant de lancer l’analyse.

Une fois connecté, appelle get_capabilities pour repérer les outils disponibles. Pour les données Google, vérifie l’accès et la propriété de mon site avec list_properties ; get_capabilities seul ne prouve pas cet accès. Si nécessaire, guide-moi avec :
${source}/docs/google-setup.md
Configure uniquement les sources utiles. GA4 et Bing restent facultatifs ; conserve les identifiants dans la configuration locale.

Lis ce scénario de référence et utilise les outils MCP adaptés à ma demande, en respectant leurs paramètres et les sources réellement accessibles :
${source}/examples/${route.guide}.md
Si tu ne peux pas lire une référence ou appeler un outil nécessaire, explique ce qui manque. Indique les outils appelés, les périodes et les données utilisées dans ton rapport.`
    : `Use Search Console MCP tools (package gsc-mcp-tools) to carry out this analysis.

Before starting, check that its tools are available in this conversation. If not, ask which assistant I use, then guide me through installing the package with uv tool install gsc-mcp-tools, registering its executable in my MCP client and restarting or reconnecting the client. Follow this guide:
${source}/docs/installation.md
Wait until the connection is verified before starting the analysis.

Once connected, call get_capabilities to identify the available tools. For Google data, verify access and my site's property with list_properties; get_capabilities alone does not prove that access. If needed, guide me using:
${source}/docs/google-setup.md
Configure only the sources needed. GA4 and Bing remain optional; keep credentials in the local configuration.

Read this reference workflow and use the MCP tools suited to my request, following their parameters and the sources actually available:
${source}/examples/${route.guide}.md
If you cannot read a reference or call a necessary tool, explain what is missing. Include the tools called, periods and data used in your report.`
  return `${instructions}\n\n${route.prompt}`
}

export const seoRoutes = {
  en: [
    {
      id: 'getting-started', problem: 'I’m new to SEO: where do I start?', analysis: 'Assess your site and explain what matters',
      result: 'Your first actions and what to measure', resultCopy: 'A starting assessment, three priorities and a simple way to track progress.',
      sources: 'Start with your site’s public pages. Connect Google Search Console to measure search visibility and clicks. GA4 and Bing are optional; your assistant explains what it can check with the available data.',
      guide: 'quick-audit',
      prompt: `My site: https://example.com (replace with your site).

I know nothing about SEO. Help me improve how people find my site in search: where should I start, what should I analyze, how should I analyze it, and what should I measure? Ask about my site’s goal and audience if you need that context.

Start by inspecting the home page and a small sample of important public pages. Explain what you check and why, without jargon. If Google Search Console is connected, use the latest complete 28 days as a starting point for clicks, impressions, click-through rate and average position. Define each metric in plain language. If data is missing, explain how to connect the needed source and what remains unknown; do not require GA4 or Bing to start.

Give me three prioritized actions, with the affected page, the issue, the suggested change and the reason to start there. For each action, explain what to measure and how to compare a later equivalent period with the starting point. Distinguish observed facts from hypotheses, and explain that average position alone is not enough to assess progress.

Do not apply changes or promise ranking gains.`,
      example: 'You get a starting assessment, such as a title to clarify on an important page, then a plan to track its clicks, impressions and click-through rate before and after the change. Missing search data is explained rather than estimated.',
    },
    {
      id: 'traffic', problem: 'My traffic is dropping', analysis: 'Analyze recent changes',
      result: 'A diagnosis and affected pages', resultCopy: 'Clicks, positions and possible causes, with supporting metrics.',
      sources: 'Google Search Console for comparable periods. GA4 can add visitor behavior; Bing is included only where the requested comparison is supported.',
      guide: 'traffic-drop',
      prompt: `My site: https://example.com (replace with your site).

Compare the latest complete 28 days with the previous 28 days. Identify the pages and queries losing clicks, and compare their impressions, click-through rate and positions.

Explain the possible causes in plain language, separating observed facts from hypotheses. Use only the sources I have connected; report missing or non-comparable data instead of guessing.

Give me a prioritized list of investigations and suggested fixes, with the affected URL and supporting metrics. Do not apply changes.`,
      example: 'If a page loses clicks while its positions stay stable, the report can recommend checking its click-through rate and search demand before assuming a ranking loss.',
    },
    {
      id: 'rankings', problem: 'I want better search rankings', analysis: 'Find ranking opportunities',
      result: 'A prioritized list of fixes', resultCopy: 'Pages to work on, with suggested title, content or internal-link changes.',
      sources: 'Google Search Console or configured Bing search metrics, plus public-page audits. GA4 is optional for visitor behavior.',
      guide: 'keyword-opportunities',
      prompt: `My site: https://example.com (replace with your site).

Find pages close to page one and pages with impressions but few clicks. Use only the search data I have connected and state the observed period.

Inspect the relevant pages before recommending changes to titles, descriptions, content or internal links. Prioritize the fixes and give the affected URL, target query and supporting metrics for each one.

Explain the recommendations without SEO jargon and suggest how to compare results after the changes. Do not apply changes or promise ranking gains.`,
      example: 'For a page with impressions but few clicks, the report can propose a title that better matches its main query and explain which metrics to compare after the rewrite.',
    },
    {
      id: 'indexing', problem: 'My pages are hard to find', analysis: 'Check indexing and technical SEO',
      result: 'Issues and suggested corrections', resultCopy: 'Indexing evidence, page checks and the next action for each issue.',
      sources: 'Public pages for technical audits. Google Search Console for indexing status; configured Bing data can add crawl signals.',
      guide: 'indexing-issues',
      prompt: `My site: https://example.com (replace with your site).

Help me understand why my pages are hard to find in search. Inspect Google indexing where Search Console is connected, and check the public pages for robots, canonical, sitemap, metadata and internal-link issues.

Distinguish crawl signals from indexing status. Explain what was checked and what remains unknown; do not infer an indexing verdict from Bing crawl data or an accepted submission.

List the affected URLs, the evidence for each issue and the suggested correction in plain language. Do not change pages or submit URLs.`,
      example: 'If a canonical tag points to a different URL than intended, the report can recommend reviewing the canonical and internal links, then inspecting the URL again.',
    },
  ],
  fr: [
    {
      id: 'getting-started', problem: 'Je débute en SEO : par où commencer ?', analysis: 'Faire le point et comprendre quoi analyser',
      result: 'Mes premières actions et quoi mesurer', resultCopy: 'Un état des lieux, trois priorités et une méthode simple pour suivre les progrès.',
      sources: 'Commencez avec les pages publiques de votre site. Connectez Google Search Console pour mesurer votre visibilité et vos clics dans Google. GA4 et Bing sont facultatifs ; votre assistant explique ce qu’il peut vérifier avec les données disponibles.',
      guide: 'quick-audit',
      prompt: `Mon site : https://example.com (à remplacer par mon site).

Je ne connais rien au SEO. Aide-moi à améliorer la visibilité de mon site dans les moteurs de recherche : par où commencer, quoi analyser, comment l’analyser et quoi mesurer ? Demande-moi l’objectif du site et son public si ce contexte te manque.

Commence par examiner la page d’accueil et un petit échantillon de pages importantes. Explique ce que tu vérifies et pourquoi, sans jargon. Si Google Search Console est connecté, utilise les 28 derniers jours complets comme point de départ pour les clics, impressions, taux de clic et position moyenne. Définis chaque métrique en langage courant. S’il manque des données, explique comment connecter la source nécessaire et ce qui reste inconnu ; ne demande pas GA4 ou Bing pour commencer.

Donne-moi trois actions prioritaires, avec la page concernée, le problème, le changement proposé et la raison de commencer par là. Pour chacune, explique quoi mesurer et comment comparer une période équivalente après le changement avec le point de départ. Distingue faits observés et hypothèses, et explique pourquoi la position moyenne ne suffit pas à évaluer les progrès.

N’applique aucun changement et ne promets pas de gain de classement.`,
      example: 'Vous obtenez un état des lieux, par exemple un titre à clarifier sur une page importante, puis un suivi de ses clics, impressions et taux de clic avant et après le changement. Les données de recherche manquantes sont expliquées plutôt qu’estimées.',
    },
    {
      id: 'traffic', problem: 'Mon trafic baisse', analysis: 'Analyser les évolutions',
      result: 'Un diagnostic et les pages concernées', resultCopy: 'Clics, positions et causes possibles, avec les métriques observées.',
      sources: 'Google Search Console pour comparer les périodes. GA4 peut ajouter le comportement des visiteurs ; Bing est inclus lorsque la comparaison demandée est disponible.',
      guide: 'traffic-drop',
      prompt: `Mon site : https://example.com (à remplacer par mon site).

Compare les 28 derniers jours complets aux 28 jours précédents. Identifie les pages et requêtes qui perdent des clics, puis compare leurs impressions, leur taux de clic et leurs positions.

Explique les causes possibles en langage courant, en distinguant faits observés et hypothèses. Utilise les sources que j’ai connectées et signale les données manquantes ou non comparables au lieu de deviner.

Propose une liste priorisée de vérifications et de correctifs avec l’URL concernée et les métriques observées. N’applique aucun changement.`,
      example: 'Si une page perd des clics alors que ses positions restent stables, le rapport peut proposer de vérifier son taux de clic et la demande de recherche avant de conclure à une perte de classement.',
    },
    {
      id: 'rankings', problem: 'Je veux mieux me positionner', analysis: 'Repérer les opportunités',
      result: 'Une liste de correctifs priorisés', resultCopy: 'Pages à travailler et changements proposés sur les titres, le contenu ou les liens internes.',
      sources: 'Métriques Google Search Console ou Bing configuré, et audits des pages publiques. GA4 est facultatif pour le comportement des visiteurs.',
      guide: 'keyword-opportunities',
      prompt: `Mon site : https://example.com (à remplacer par mon site).

Repère les pages proches de la première page et celles qui ont des impressions mais peu de clics. Utilise les données de recherche que j’ai connectées et indique la période observée.

Inspecte les pages concernées avant de proposer des changements de titres, descriptions, contenu ou liens internes. Priorise les correctifs et donne pour chacun l’URL, la requête visée et les métriques observées.

Explique tes recommandations sans jargon SEO et propose comment comparer les résultats après les changements. N’applique aucun changement et ne promets pas de gain de classement.`,
      example: 'Pour une page visible mais peu cliquée, le rapport peut proposer un titre qui correspond mieux à sa requête principale et préciser les métriques à comparer après la réécriture.',
    },
    {
      id: 'indexing', problem: 'Mes pages sont peu visibles', analysis: 'Vérifier l’indexation et la technique',
      result: 'Des problèmes et leurs correctifs', resultCopy: 'État d’indexation, contrôles des pages et prochaine action pour chaque problème.',
      sources: 'Pages publiques pour les audits techniques. Google Search Console pour l’état d’indexation ; Bing configuré peut ajouter des signaux d’exploration.',
      guide: 'indexing-issues',
      prompt: `Mon site : https://example.com (à remplacer par mon site).

Aide-moi à comprendre pourquoi mes pages sont peu visibles dans les moteurs de recherche. Vérifie leur indexation Google si Search Console est connecté et audite les pages publiques : robots, canonical, sitemap, métadonnées et liens internes.

Distingue les signaux d’exploration de l’état d’indexation. Explique ce qui a été vérifié et ce qui reste inconnu ; ne déduis pas l’indexation des données d’exploration Bing ou d’une soumission acceptée.

Liste les URL concernées, les preuves de chaque problème et le correctif proposé en langage courant. Ne modifie pas les pages et ne soumets aucune URL.`,
      example: 'Si une balise canonical pointe vers une autre URL que celle prévue, le rapport peut proposer de vérifier la canonical et les liens internes, puis d’inspecter à nouveau l’URL.',
    },
  ],
} as const
