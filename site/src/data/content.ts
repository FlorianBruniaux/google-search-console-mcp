export type Locale = 'en' | 'fr'

const externalLinks = {
  repository: 'https://github.com/FlorianBruniaux/google-search-console-mcp',
  pypi: 'https://pypi.org/project/gsc-mcp-tools/',
  licenseSource: 'https://github.com/FlorianBruniaux/google-search-console-mcp/blob/main/LICENSE',
  author: 'https://www.florian.bruniaux.com/about/?utm_source=search-console-mcp&utm_medium=website',
  portfolio: 'https://www.florian.bruniaux.com/',
  projects: 'https://www.florian.bruniaux.com/projects/',
  blog: 'https://www.florian.bruniaux.com/blog/',
  githubProfile: 'https://github.com/FlorianBruniaux',
  linkedin: 'https://www.linkedin.com/in/florian-bruniaux-43408b83/',
  claudeGuide: 'https://cc.bruniaux.com/',
  starmapper: 'https://starmapper.bruniaux.com/',
  ccboard: 'https://ccboard.bruniaux.com/',
  ccbridge: 'https://ccbridge.bruniaux.com/',
  youtubeInsights: 'https://github.com/FlorianBruniaux/youtube-video-insights',
} as const

const localizedPaths = {
  en: {
    home: '/', otherHome: '/fr/', docs: '/docs/', install: '/docs/installation/', googleSetup: '/docs/google-setup/',
    bingSetup: '/docs/bing-setup/', starterPrompts: '/docs/prompts/', changelog: '/docs/changelog/',
    architecture: '/docs/architecture/', bingContract: '/docs/evidence-and-safety/', license: '/docs/license/',
  },
  fr: {
    home: '/fr/', otherHome: '/', docs: '/fr/docs/', install: '/fr/docs/installation/', googleSetup: '/fr/docs/google-setup/',
    bingSetup: '/fr/docs/bing-setup/', starterPrompts: '/fr/docs/prompts/', changelog: '/fr/docs/changelog/',
    architecture: '/fr/docs/architecture/', bingContract: '/fr/docs/evidence-and-safety/', license: '/fr/docs/license/',
  },
} as const

export const siteLinks = { ...externalLinks, ...localizedPaths.en, docsFr: localizedPaths.fr.docs } as const

export function getSiteLinks(locale: Locale) {
  return { ...externalLinks, ...localizedPaths[locale] }
}

export const landingContent = {
  en: {
    seo: {
      title: 'Search Console MCP for Google, Bing and SEO Analytics',
      description: 'Connect AI assistants to Google Search Console, Bing Webmaster Tools, GA4, CrUX and guarded SEO workflows.',
      imageAlt: 'Search Console MCP: Google, Bing and SEO analytics for AI assistants. Connect, Measure, Compare, Explain, Submit.',
    },
    header: {
      skip: 'Skip to main content', home: 'Search Console MCP home', open: 'Open navigation', close: 'Close navigation',
      explore: 'Explore Search Console MCP', navigation: 'Primary navigation', install: 'Install', docs: 'Docs', language: 'FR', languageCode: 'fr',
      external: 'opens in a new tab', themeDark: 'Switch to dark theme', themeLight: 'Switch to light theme',
    },
    hero: {
      kicker: 'Google + Bing + SEO analytics', title: 'Search data your AI assistant can inspect, compare and act on safely.',
      copy: 'Search Console MCP connects Claude, Codex and other MCP clients to Google Search Console, Bing Webmaster Tools, GA4, CrUX, IndexNow and public-page audits.',
      copyCommand: 'Copy uvx command', installPath: 'View installation path', intentsLabel: 'Common SEO workflows',
      intents: [['Compare Google and Bing', '#capabilities'], ['Diagnose indexing', '#safety'], ['Audit a public page', '#provider-public']],
      terminalLabel: 'Example command and request', terminalPrompt: "Compare this site's Google and Bing visibility. Keep each provider's position semantics separate.",
      terminalResult: 'registered tools, structured JSON output',
    },
    proof: {
      label: 'Package facts',
      items: [['MCP tools', 'Registered in the server'], ['Google + Bing', 'Provider semantics stay separate'], ['Structured JSON', 'Machine-readable responses'], ['Guarded writes', 'Explicit target and action']],
    },
    capabilities: {
      kicker: '01 / Capabilities', title: 'Three sources. Explicit boundaries.', intro: 'Start with the evidence your question needs.',
      providers: [
        { id: 'google', title: 'Google data', copy: 'Search Console performance and inspection, optional GA4 behavior data, and optional CrUX field data.', items: ['Search performance', 'URL inspection', 'GA4', 'CrUX'] },
        { id: 'bing', title: 'Bing data', copy: 'Webmaster performance, crawl, feeds, backlinks and guarded submissions for sites visible to the configured Bing account.', items: ['Queries and pages', 'Crawl signals', 'Feeds', 'IndexNow'] },
        { id: 'public', title: 'Public-page analysis', copy: 'Fetched HTML, robots, sitemaps, structured data, content and internal-link signals without private provider credentials.', items: ['Metadata', 'Schema', 'Sitemaps', 'Internal links'] },
      ], boundary: 'Google and Bing position semantics remain separate.',
    },
    workflow: {
      kicker: '02 / Workflow', title: 'From a question to a checked action.',
      steps: [['Connect', 'Select only the verified properties and provider credentials you need.'], ['Measure', 'Read queries, pages, crawl signals and public-page evidence.'], ['Compare', 'Keep provider semantics and observed windows explicit.'], ['Explain', 'Return structured facts, derived values and recommendations.'], ['Submit', 'Run bounded write tools only after the target and action are confirmed.']],
    },
    install: {
      kicker: '03 / Get started', title: 'A small setup. A deliberate first check.', intro: 'Choose an install path, connect your MCP client, then verify provider access.',
      steps: [['Evaluate once', 'Run uvx gsc-mcp-tools without changing a project environment.'], ['Install persistently', 'Run uv tool install gsc-mcp-tools and point the MCP client at the installed executable.'], ['Verify access', 'Run gsc-cli list, then verify each configured provider separately.']],
      copyLabels: ['Copy evaluate command', 'Copy persistent install command', 'Copy verification command'], expected: 'Expected: the registered commands and their one-line descriptions.', guide: 'Read the client-specific installation guide',
    },
    evidence: {
      kicker: '04 / Evidence & safety', title: 'Know what the result proves.', intro: 'An accepted submission proves neither crawl nor indexation.', guide: 'Read the Bing API contract',
      states: [['Observed', 'API responses and fetched public-page data.'], ['Derived', 'Calculations tied to an explicit observed window.'], ['Requested', 'A provider accepted a submission. Crawl and indexation remain unproven.']],
    },
    faq: {
      kicker: '05 / FAQ', title: 'Before you connect.',
      items: [
        { question: 'Does one Bing API key work for every site?', answer: 'One Bing Webmaster API key can access the verified sites visible to that Bing account. Every tool call still names its target site. IndexNow uses a different key verified on each target host.' },
        { question: 'Do I need every Google API enabled?', answer: 'No. Configure the provider families you use. Search Console credentials cover the core search workflows. GA4, CrUX and eligible Indexing API workflows require their own optional configuration.' },
        { question: 'Does a successful submission mean the page is indexed?', answer: 'No. An accepted submission proves only that the provider accepted the request. Crawl and indexation must be measured separately in a later comparable check.' },
        { question: 'Can I use the server from Claude and Codex?', answer: 'Yes. Search Console MCP runs over stdio and can be configured in Claude, Codex and other compatible MCP clients. The executable path and configuration format depend on the client.' },
        { question: 'Where do credentials live?', answer: 'Credentials stay in the MCP server environment or the client configuration. The public website never receives them, and prompts should not contain secret values.' },
      ],
    },
    final: { kicker: 'Ready to connect?', title: 'Install Search Console MCP.', copy: 'Start with the package, then connect only the providers your workflow needs.', button: 'Copy final uvx command', guide: 'Read the installation guide' },
    footer: {
      tagline: 'Search evidence, with its limits attached.', creator: 'Open-source AI engineering by', groups: { navigate: 'Navigate', product: 'Product', ecosystem: 'Ecosystem' },
      nav: [['Overview', '#main-content'], ['Providers', '#capabilities'], ['Workflow', '#workflow'], ['Install', '#install'], ['Safety', '#safety'], ['FAQ', '#faq']],
      product: ['Documentation', 'GitHub', 'PyPI', 'Installation docs', 'Changelog', 'MIT license'], ecosystem: ['All projects', 'Claude Code Guide', 'StarMapper', 'CCBoard', 'CC-Copilot Bridge', 'YT Insights'],
      creatorLinks: ['Portfolio', 'Blog', 'GitHub profile', 'LinkedIn'], external: 'opens in a new tab',
    },
  },
  fr: {
    seo: {
      title: "Search Console MCP pour Google, Bing et l’analyse SEO",
      description: 'Connectez vos assistants IA à Google Search Console, Bing Webmaster Tools, GA4, CrUX et à des workflows SEO contrôlés.',
      imageAlt: 'Search Console MCP : analytics Google, Bing et SEO pour assistants IA. Connecter, Mesurer, Comparer, Expliquer, Soumettre.',
    },
    header: {
      skip: 'Aller au contenu principal', home: 'Accueil Search Console MCP', open: 'Ouvrir la navigation', close: 'Fermer la navigation',
      explore: 'Explorer Search Console MCP', navigation: 'Navigation principale', install: 'Installer', docs: 'Documentation', language: 'EN', languageCode: 'en',
      external: 'ouvre un nouvel onglet', themeDark: 'Passer au thème sombre', themeLight: 'Passer au thème clair',
    },
    hero: {
      kicker: 'Google + Bing + analytics SEO', title: 'Les données de recherche que votre assistant IA peut inspecter, comparer et exploiter en toute sécurité.',
      copy: 'Search Console MCP connecte Claude, Codex et les autres clients MCP à Google Search Console, Bing Webmaster Tools, GA4, CrUX, IndexNow et aux audits de pages publiques.',
      copyCommand: 'Copier la commande uvx', installPath: "Voir le parcours d’installation", intentsLabel: 'Workflows SEO courants',
      intents: [['Comparer Google et Bing', '#capabilities'], ["Diagnostiquer l’indexation", '#safety'], ['Auditer une page publique', '#provider-public']],
      terminalLabel: 'Exemple de commande et de requête', terminalPrompt: 'Compare la visibilité Google et Bing de ce site. Garde distincte la sémantique de position de chaque moteur.', terminalResult: 'outils enregistrés, sortie JSON structurée',
    },
    proof: {
      label: 'Informations sur le package',
      items: [['outils MCP', 'Enregistrés dans le serveur'], ['Google + Bing', 'Sémantiques des moteurs séparées'], ['JSON structuré', 'Réponses lisibles par machine'], ['Écritures contrôlées', 'Cible et action explicites']],
    },
    capabilities: {
      kicker: '01 / Capacités', title: 'Trois sources. Des limites explicites.', intro: 'Commencez par les preuves nécessaires à votre question.',
      providers: [
        { id: 'google', title: 'Données Google', copy: 'Performances et inspection Search Console, données comportementales GA4 facultatives et données terrain CrUX facultatives.', items: ['Performances de recherche', 'Inspection d’URL', 'GA4', 'CrUX'] },
        { id: 'bing', title: 'Données Bing', copy: 'Performances Webmaster, exploration, flux, backlinks et soumissions contrôlées pour les sites visibles par le compte Bing configuré.', items: ['Requêtes et pages', 'Signaux d’exploration', 'Flux', 'IndexNow'] },
        { id: 'public', title: 'Analyse des pages publiques', copy: 'HTML, robots, sitemaps, données structurées, contenu et liens internes, sans identifiants privés des moteurs.', items: ['Métadonnées', 'Schema', 'Sitemaps', 'Liens internes'] },
      ], boundary: 'Les sémantiques de position Google et Bing restent séparées.',
    },
    workflow: {
      kicker: '02 / Workflow', title: 'De la question à une action vérifiée.',
      steps: [['Connecter', 'Sélectionnez uniquement les propriétés vérifiées et les identifiants nécessaires.'], ['Mesurer', 'Lisez les requêtes, pages, signaux d’exploration et preuves issues des pages publiques.'], ['Comparer', 'Gardez explicites la sémantique des moteurs et les périodes observées.'], ['Expliquer', 'Retournez des faits structurés, des valeurs calculées et des recommandations.'], ['Soumettre', 'N’exécutez les outils d’écriture qu’après confirmation de la cible et de l’action.']],
    },
    install: {
      kicker: '03 / Démarrer', title: 'Une configuration réduite. Un premier contrôle volontaire.', intro: 'Choisissez une méthode d’installation, connectez votre client MCP, puis vérifiez chaque moteur.',
      steps: [['Évaluer une fois', 'Lancez uvx gsc-mcp-tools sans modifier l’environnement du projet.'], ['Installer durablement', 'Lancez uv tool install gsc-mcp-tools et configurez votre client MCP avec cet exécutable.'], ['Vérifier les accès', 'Lancez gsc-cli list, puis vérifiez séparément chaque moteur configuré.']],
      copyLabels: ["Copier la commande d’évaluation", "Copier la commande d’installation", 'Copier la commande de vérification'], expected: 'Résultat attendu : les commandes enregistrées et leur description sur une ligne.', guide: "Lire le guide d’installation par client",
    },
    evidence: {
      kicker: '04 / Preuves et sécurité', title: 'Sachez ce que le résultat prouve.', intro: "Une soumission acceptée ne prouve ni l’exploration ni l’indexation.", guide: 'Lire le contrat de l’API Bing',
      states: [['Observé', 'Réponses des API et données issues des pages publiques.'], ['Calculé', 'Calculs liés à une période observée explicite.'], ['Demandé', "Un moteur a accepté une soumission. L’exploration et l’indexation restent à prouver."]],
    },
    faq: {
      kicker: '05 / FAQ', title: 'Avant de vous connecter.',
      items: [
        { question: 'Une clé API Bing fonctionne-t-elle pour tous les sites ?', answer: 'Une clé API Bing Webmaster peut accéder aux sites vérifiés visibles par le compte Bing associé. Chaque appel précise toujours le site cible. IndexNow utilise une autre clé, vérifiée sur chaque hôte cible.' },
        { question: 'Dois-je activer toutes les API Google ?', answer: 'Non. Configurez uniquement les familles de moteurs utilisées. Les identifiants Search Console couvrent les workflows de recherche principaux. GA4, CrUX et les workflows éligibles de l’API Indexing nécessitent leur propre configuration facultative.' },
        { question: 'Une soumission réussie signifie-t-elle que la page est indexée ?', answer: "Non. Une soumission acceptée prouve uniquement que le moteur a accepté la demande. L’exploration et l’indexation doivent être mesurées séparément lors d’un contrôle ultérieur comparable." },
        { question: 'Puis-je utiliser le serveur depuis Claude et Codex ?', answer: 'Oui. Search Console MCP fonctionne en stdio et peut être configuré dans Claude, Codex et les autres clients MCP compatibles. Le chemin de l’exécutable et le format de configuration dépendent du client.' },
        { question: 'Où sont stockés les identifiants ?', answer: 'Les identifiants restent dans l’environnement du serveur MCP ou dans la configuration du client. Le site public ne les reçoit jamais et les prompts ne doivent pas contenir de secrets.' },
      ],
    },
    final: { kicker: 'Prêt à vous connecter ?', title: 'Installez Search Console MCP.', copy: 'Commencez par le package, puis connectez uniquement les moteurs nécessaires à votre workflow.', button: 'Copier la commande uvx finale', guide: "Lire le guide d’installation" },
    footer: {
      tagline: 'Les preuves de recherche, avec leurs limites.', creator: 'Ingénierie IA open source par', groups: { navigate: 'Navigation', product: 'Produit', ecosystem: 'Écosystème' },
      nav: [['Vue d’ensemble', '#main-content'], ['Moteurs', '#capabilities'], ['Workflow', '#workflow'], ['Installation', '#install'], ['Sécurité', '#safety'], ['FAQ', '#faq']],
      product: ['Documentation', 'GitHub', 'PyPI', "Guide d’installation", 'Historique', 'Licence MIT'], ecosystem: ['Tous les projets', 'Guide Claude Code', 'StarMapper', 'CCBoard', 'CC-Copilot Bridge', 'YT Insights'],
      creatorLinks: ['Portfolio', 'Blog', 'Profil GitHub', 'LinkedIn'], external: 'ouvre un nouvel onglet',
    },
  },
} as const
