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
    sitemap: '/sitemap/', updates: '/updates/',
  },
  fr: {
    home: '/fr/', otherHome: '/', docs: '/fr/docs/', install: '/fr/docs/installation/', googleSetup: '/fr/docs/google-setup/',
    bingSetup: '/fr/docs/bing-setup/', starterPrompts: '/fr/docs/prompts/', changelog: '/fr/docs/changelog/',
    architecture: '/fr/docs/architecture/', bingContract: '/fr/docs/evidence-and-safety/', license: '/fr/docs/license/',
    sitemap: '/fr/sitemap/', updates: '/fr/updates/',
  },
} as const

export const siteLinks = { ...externalLinks, ...localizedPaths.en, docsFr: localizedPaths.fr.docs } as const

export function getSiteLinks(locale: Locale) {
  return { ...externalLinks, ...localizedPaths[locale] }
}

export const landingContent = {
  en: {
    seo: {
      title: 'Search Console MCP: AI-Powered SEO Audits for Google and Bing',
      description: 'Automate SEO audits with Claude or Codex. Use your Google and Bing data to find prioritized fixes and improve your search visibility, without needing SEO expertise.',
      imageAlt: 'Search Console MCP: Google, Bing and SEO analytics for AI assistants. Connect, Measure, Compare, Explain, Submit.',
    },
    header: {
      skip: 'Skip to main content', home: 'Search Console MCP home', open: 'Open navigation', close: 'Close navigation',
      explore: 'Explore Search Console MCP', navigation: 'Primary navigation', install: 'Install', docs: 'Docs', language: 'FR', languageCode: 'fr',
      external: 'opens in a new tab', themeDark: 'Switch to dark theme', themeLight: 'Switch to light theme',
    },
    hero: {
      kicker: 'Automate SEO audits with Claude or Codex', title: 'Improve your search visibility with AI.',
      copy: 'Let Claude or Codex retrieve your Google and Bing data, audit your pages and recommend the fixes to prioritize. Less manual checking, a clear action plan, no SEO expertise required.',
      evidenceTitle: 'Unavailable metrics are reported as unavailable.',
      evidenceLink: 'Read the data limits',
      setup: 'Connect your accounts once, then ask in plain language. You review the proposed fixes and track the results.',
      copyCommand: 'Copy uvx command', installPath: 'View installation path', intentsLabel: 'Common SEO workflows',
      intents: [['Start with SEO', '#seo-getting-started'], ['Understand a traffic drop', '#seo-traffic'], ['Find ranking opportunities', '#seo-rankings'], ['Check page visibility', '#seo-indexing']],
      terminalLabel: 'Example SEO request and suggested output', terminalPrompt: 'Audit my site and give me the three fixes to prioritize for Google and Bing.',
      exampleLabel: 'Illustrative output, not a live site report',
      exampleItems: [['Explain a traffic drop', 'Compare clicks and positions, then identify possible causes.'], ['Improve a search snippet', 'Suggest a title rewrite for a page with impressions but few clicks.'], ['Help a page rank higher', 'Find pages close to page one and suggest content or internal-link changes.']],
      terminalResult: 'registered tools, structured JSON output',
    },
    outcomes: {
      kicker: 'Choose your starting point', title: 'One problem, one analysis, actionable fixes.',
      intro: 'New to SEO? Start with a site assessment to learn what to analyze and measure. Choose your problem, then ask Claude or Codex. Search Console MCP supplies the data and page audits for the analysis.',
      columns: ['Your problem', 'Your assistant analyzes', 'What you get'],
      open: 'See the prompt', detailTitle: 'Prompts to use in your assistant', sourcesLabel: 'Data needed',
      setupTitle: 'Before running the analysis', setupHelp: 'Paste this prompt into a compatible AI assistant. It asks the assistant to use Search Console MCP, verify the connection and guide setup if needed. The setup instructions and GitHub workflow links are included in the copied text.',
      setupInstall: 'Install the MCP', setupGoogle: 'Connect Google', sourceLabel: 'View the workflow on GitHub',
      promptLabel: 'Prompt to copy', replaceSite: 'Replace https://example.com with your site before sending. You can copy the prompt or select its text.',
      copyPrompt: 'Copy prompt', exampleLabel: 'Illustrative example; the actual report depends on your data', guideLabel: 'Read the full workflow',
      boundary: 'The server fetches data and runs analyses. Your AI assistant explains the results and proposes fixes. A coding assistant with repository access can help apply the changes you choose.',
    },
    proof: {
      label: 'Package facts',
      items: [['MCP tools', 'Registered in the server'], ['Google + Bing', 'Provider semantics stay separate'], ['Structured JSON', 'Machine-readable responses'], ['Guarded writes', 'Explicit target and action']],
    },
    capabilities: {
      kicker: '01 / Data behind the analysis', title: 'See where visibility is lost and why pages need attention.', intro: 'Connect the sources you use. Your assistant can combine search performance, visitor behavior and page audits to guide its recommendations.',
      providers: [
        { id: 'google', title: 'Google data', copy: 'Find which searches bring visitors and which pages lose clicks or positions with Search Console. Optional GA4 shows what visitors do next; CrUX adds real-user loading and interaction metrics.', items: ['Search performance', 'URL inspection', 'GA4', 'CrUX'] },
        { id: 'bing', title: 'Bing data', copy: 'Find opportunities in Bing search and investigate crawl issues for your verified sites. Compare Google and Bing visibility to see where each engine needs attention.', items: ['Queries and pages', 'Crawl signals', 'Feeds', 'IndexNow'] },
        { id: 'public', title: 'Public-page analysis', copy: 'Check the pages themselves for metadata, content, structured-data and internal-link issues that may explain weak performance, without private provider credentials.', items: ['Metadata', 'Schema', 'Sitemaps', 'Internal links'] },
      ], boundary: 'Google and Bing position semantics remain separate.',
    },
    workflow: {
      kicker: '02 / Workflow', title: 'Automate the audit. Review the fixes. Track the results.',
      steps: [['Connect', 'Install in Claude, Codex or another MCP client and connect the accounts you use.'], ['Ask', 'Describe your goal in plain language, such as understanding a traffic drop or finding ranking opportunities.'], ['Analyze', 'Your assistant calls the tools, compares metrics and audits pages to propose a prioritized action plan.'], ['Fix', 'Review the recommendations. Apply them yourself or ask a coding assistant with repository access to help.'], ['Measure', 'Rerun the analysis to track changes. Schedule recurring checks through your client or an external automation.']],
    },
    install: {
      kicker: '03 / Get started', title: 'Choose 1 install path, then verify access.', intro: 'Connect your MCP client, then verify each provider separately.',
      steps: [['Evaluate once', 'Run uvx gsc-mcp-tools without changing a project environment.'], ['Install persistently', 'Run uv tool install gsc-mcp-tools and point the MCP client at the installed executable.'], ['Verify access', 'Run gsc-cli list, then verify each configured provider separately.']],
      copyLabels: ['Copy evaluate command', 'Copy persistent install command', 'Copy verification command'], expected: 'Expected: the registered commands and their one-line descriptions.', guide: 'Read the client-specific installation guide',
    },
    evidence: {
      kicker: '04 / Evidence & safety', title: '3 result states: observed, derived, requested.', intro: 'Unsupported Bing analyses are identified explicitly. Cross-engine deltas require exact, matching observed windows. An accepted submission proves neither crawl nor indexation.', guide: 'Read the data limits',
      states: [['Observed', 'API responses and fetched public-page data.'], ['Derived', 'Calculations tied to an explicit observed window.'], ['Requested', 'A provider accepted a submission. Crawl and indexation remain unproven.']],
    },
    faq: {
      kicker: '05 / FAQ', title: 'Using your AI assistant for SEO.',
      items: [
        { question: 'What comes out of an analysis?', answer: 'Your assistant can turn the tool results into a diagnosis of recent SEO changes and a prioritized action plan: affected pages, supporting metrics, suggested title or content edits, internal-link changes and technical issues to investigate. The output depends on your prompt and the data available.' },
        { question: 'Do I need SEO expertise?', answer: 'You can ask in plain language and have the assistant explain the metrics and recommendations. Initial installation and account setup are required; the guides walk through them. You still review suggested fixes before applying them.' },
        { question: 'Does it automatically improve my rankings?', answer: 'It automates data retrieval and provides analyses that your assistant uses to suggest fixes. A coding assistant can help apply approved changes when it has repository access. Recurring runs require a scheduler or client automation. Ranking gains are not guaranteed; compare your metrics after the changes.' },
        { question: 'Can 1 Bing API key cover several sites?', answer: 'One Bing Webmaster API key can access the verified sites visible to that Bing account. Every tool call still names its target site. IndexNow uses a different key verified on each target host.' },
        { question: 'Which Google APIs do I need?', answer: 'Configure only the provider families you use. Search Console credentials cover the core search workflows. GA4, CrUX and eligible Indexing API workflows require their own optional configuration.' },
        { question: 'Does an accepted submission prove indexation?', answer: 'No. It proves only that the provider accepted the request. Measure crawl and indexation separately in a later comparable check.' },
        { question: 'Can I use Search Console MCP with Claude and Codex?', answer: 'Yes. Search Console MCP runs over stdio and works with Claude, Codex and other compatible MCP clients. The executable path and configuration format depend on the client.' },
        { question: 'Where should credentials be stored?', answer: 'Keep credentials in the MCP server environment or the client configuration. The public website never receives them, and prompts should not contain secret values.' },
      ],
    },
    final: { kicker: 'Start with your own site.', title: 'Get your first SEO action plan.', copy: 'Connect your accounts and let Claude or Codex run your first audit. Get prioritized fixes to improve your search visibility.', button: 'Copy final uvx command', guide: 'Read the installation guide' },
    footer: {
      tagline: 'Automate SEO audits. Improve your search visibility with AI.', creator: 'Open-source AI engineering by', groups: { navigate: 'Navigate', product: 'Product', ecosystem: 'Ecosystem' },
      nav: [['Overview', '#main-content'], ['Choose a problem', '#outcomes'], ['Providers', '#capabilities'], ['Workflow', '#workflow'], ['Install', '#install'], ['Safety', '#safety'], ['FAQ', '#faq']],
      product: ['Documentation', 'GitHub', 'PyPI', 'Installation docs', 'Changelog', 'MIT license'], ecosystem: ['All projects', 'Claude Code Guide', 'StarMapper', 'CCBoard', 'CC-Copilot Bridge', 'YT Insights'],
      creatorLinks: ['Portfolio', 'Blog', 'GitHub profile', 'LinkedIn'], external: 'opens in a new tab',
    },
  },
  fr: {
    seo: {
      title: "Search Console MCP : audits SEO avec l’IA pour Google et Bing",
      description: 'Automatisez vos audits SEO avec Claude ou Codex. Obtenez les corrections prioritaires pour améliorer votre visibilité sur Google et Bing, sans expertise SEO requise.',
      imageAlt: 'Search Console MCP : analytics Google, Bing et SEO pour assistants IA. Connecter, Mesurer, Comparer, Expliquer, Soumettre.',
    },
    header: {
      skip: 'Aller au contenu principal', home: 'Accueil Search Console MCP', open: 'Ouvrir la navigation', close: 'Fermer la navigation',
      explore: 'Explorer Search Console MCP', navigation: 'Navigation principale', install: 'Installer', docs: 'Documentation', language: 'EN', languageCode: 'en',
      external: 'ouvre un nouvel onglet', themeDark: 'Passer au thème sombre', themeLight: 'Passer au thème clair',
    },
    hero: {
      kicker: 'Automatisez vos audits SEO avec Claude ou Codex', title: 'Améliorez votre référencement avec l’IA.',
      copy: 'Laissez Claude ou Codex récupérer vos données Google et Bing, auditer vos pages et proposer les corrections prioritaires. Moins de vérifications manuelles, un plan d’action clair, sans expertise SEO requise.',
      evidenceTitle: 'Les métriques indisponibles sont signalées comme indisponibles.',
      evidenceLink: 'Lire les limites des données',
      setup: 'Connectez vos comptes une fois, puis posez vos questions en langage courant. Vous validez les corrections et suivez les résultats.',
      copyCommand: 'Copier la commande uvx', installPath: "Voir le parcours d’installation", intentsLabel: 'Workflows SEO courants',
      intents: [['Débuter en SEO', '#seo-getting-started'], ['Comprendre une baisse de trafic', '#seo-traffic'], ['Trouver des opportunités', '#seo-rankings'], ['Vérifier la visibilité des pages', '#seo-indexing']],
      terminalLabel: 'Exemple de demande SEO et de résultat proposé', terminalPrompt: 'Audite mon site et donne-moi les trois corrections prioritaires pour Google et Bing.', terminalResult: 'outils enregistrés, sortie JSON structurée',
      exampleLabel: 'Exemple illustratif, pas un rapport sur un site réel',
      exampleItems: [['Expliquer une baisse de trafic', 'Comparer les clics et les positions, puis identifier les causes possibles.'], ['Améliorer un résultat de recherche', 'Proposer un nouveau titre pour une page visible mais peu cliquée.'], ['Aider une page à mieux se positionner', 'Repérer les pages proches de la première page et proposer des changements de contenu ou de liens internes.']],
    },
    outcomes: {
      kicker: 'Choisissez votre point d’entrée', title: 'Un problème, une analyse, des correctifs.',
      intro: 'Vous débutez en SEO ? Commencez par un état des lieux pour savoir quoi analyser et mesurer. Choisissez votre problème, puis posez la question à Claude ou Codex. Search Console MCP lui fournit les données et les audits de pages pour mener l’analyse.',
      columns: ['Votre problème', 'Votre assistant analyse', 'Ce que vous obtenez'],
      open: 'Voir le prompt', detailTitle: 'Les prompts à utiliser dans votre assistant', sourcesLabel: 'Données nécessaires',
      setupTitle: 'Avant de lancer l’analyse', setupHelp: 'Collez ce prompt dans un assistant IA compatible. Il lui demande d’utiliser Search Console MCP, de vérifier la connexion et de vous guider si la configuration manque. Les instructions et les liens vers les guides GitHub sont inclus dans le texte copié.',
      setupInstall: 'Installer le MCP', setupGoogle: 'Connecter Google', sourceLabel: 'Voir le scénario sur GitHub',
      promptLabel: 'Prompt à copier', replaceSite: 'Remplacez https://example.com par votre site avant l’envoi. Vous pouvez copier le prompt ou sélectionner son texte.',
      copyPrompt: 'Copier le prompt', exampleLabel: 'Exemple illustratif ; le rapport réel dépend de vos données', guideLabel: 'Lire le scénario complet',
      boundary: 'Le serveur récupère les données et lance les analyses. Votre assistant IA explique les résultats et propose les correctifs. Un assistant de code ayant accès au dépôt peut aider à appliquer les changements que vous choisissez.',
    },
    proof: {
      label: 'Informations sur le package',
      items: [['outils MCP', 'Enregistrés dans le serveur'], ['Google + Bing', 'Sémantiques des moteurs séparées'], ['JSON structuré', 'Réponses lisibles par machine'], ['Écritures contrôlées', 'Cible et action explicites']],
    },
    capabilities: {
      kicker: '01 / Les données derrière l’analyse', title: 'Repérez où vous perdez en visibilité et quelles pages corriger.', intro: 'Connectez les sources que vous utilisez. Votre assistant peut croiser performances de recherche, comportement des visiteurs et audits de pages pour guider ses recommandations.',
      providers: [
        { id: 'google', title: 'Données Google', copy: 'Identifiez les recherches qui amènent des visiteurs et les pages qui perdent des clics ou des positions avec Search Console. GA4 ajoute leur comportement et CrUX les métriques de chargement et d’interaction, en option.', items: ['Performances de recherche', 'Inspection d’URL', 'GA4', 'CrUX'] },
        { id: 'bing', title: 'Données Bing', copy: 'Repérez les opportunités dans Bing et les problèmes d’exploration de vos sites vérifiés. Comparez la visibilité Google et Bing pour identifier les pages à travailler sur chaque moteur.', items: ['Requêtes et pages', 'Signaux d’exploration', 'Flux', 'IndexNow'] },
        { id: 'public', title: 'Analyse des pages publiques', copy: 'Vérifiez les métadonnées, le contenu, les données structurées et les liens internes qui peuvent expliquer de faibles performances, sans identifiants privés des moteurs.', items: ['Métadonnées', 'Schema', 'Sitemaps', 'Liens internes'] },
      ], boundary: 'Les sémantiques de position Google et Bing restent séparées.',
    },
    workflow: {
      kicker: '02 / Fonctionnement', title: 'Automatisez l’audit. Validez les corrections. Suivez les résultats.',
      steps: [['Connecter', 'Installez dans Claude, Codex ou un autre client MCP et connectez les comptes que vous utilisez.'], ['Demander', 'Décrivez votre objectif en langage courant : comprendre une baisse de trafic ou trouver des opportunités de classement.'], ['Analyser', 'Votre assistant appelle les outils, compare les métriques et audite les pages pour proposer un plan d’action priorisé.'], ['Corriger', 'Validez les recommandations. Appliquez-les ou demandez l’aide d’un assistant de code ayant accès au dépôt.'], ['Mesurer', 'Relancez l’analyse pour suivre les évolutions. Programmez les contrôles récurrents via votre client ou une automatisation externe.']],
    },
    install: {
      kicker: '03 / Démarrer', title: 'Choisissez 1 méthode d’installation, puis vérifiez les accès.', intro: 'Connectez votre client MCP, puis vérifiez séparément chaque moteur.',
      steps: [['Évaluer une fois', 'Lancez uvx gsc-mcp-tools sans modifier l’environnement du projet.'], ['Installer durablement', 'Lancez uv tool install gsc-mcp-tools et configurez votre client MCP avec cet exécutable.'], ['Vérifier les accès', 'Lancez gsc-cli list, puis vérifiez séparément chaque moteur configuré.']],
      copyLabels: ["Copier la commande d’évaluation", "Copier la commande d’installation", 'Copier la commande de vérification'], expected: 'Résultat attendu : les commandes enregistrées et leur description sur une ligne.', guide: "Lire le guide d’installation par client",
    },
    evidence: {
      kicker: '04 / Preuves et sécurité', title: '3 états de résultat : observé, calculé, demandé.', intro: "Les analyses Bing non prises en charge sont signalées explicitement. Les écarts entre moteurs exigent des périodes observées exactes et identiques. Une soumission acceptée ne prouve ni l’exploration ni l’indexation.", guide: 'Lire les limites des données',
      states: [['Observé', 'Réponses des API et données issues des pages publiques.'], ['Calculé', 'Calculs liés à une période observée explicite.'], ['Demandé', "Un moteur a accepté une soumission. L’exploration et l’indexation restent à prouver."]],
    },
    faq: {
      kicker: '05 / FAQ', title: 'Utiliser votre assistant IA pour le SEO.',
      items: [
        { question: 'Qu’est-ce qui sort d’une analyse ?', answer: 'Votre assistant peut transformer les résultats des outils en diagnostic des évolutions SEO et en plan d’action priorisé : pages concernées, métriques observées, changements de titres ou de contenu, liens internes et problèmes techniques à examiner. Le résultat dépend de votre demande et des données accessibles.' },
        { question: 'Faut-il une expertise SEO ?', answer: 'Vous pouvez poser vos questions en langage courant et demander à l’assistant d’expliquer les métriques et les recommandations. L’installation et la connexion initiale des comptes restent nécessaires ; les guides détaillent ces étapes. Vous validez les correctifs avant de les appliquer.' },
        { question: 'Est-ce que mon classement s’améliore automatiquement ?', answer: 'Le serveur automatise la récupération des données et fournit des analyses que votre assistant utilise pour proposer des correctifs. Un assistant de code peut aider à appliquer les changements validés s’il a accès au dépôt. Les analyses récurrentes demandent un planificateur ou une automatisation du client. Les gains de classement ne sont pas garantis : comparez vos métriques après les changements.' },
        { question: '1 clé API Bing peut-elle couvrir plusieurs sites ?', answer: 'Une clé API Bing Webmaster peut accéder aux sites vérifiés visibles par le compte Bing associé. Chaque appel précise toujours le site cible. IndexNow utilise une autre clé, vérifiée sur chaque hôte cible.' },
        { question: 'Quelles API Google dois-je activer ?', answer: 'Configurez uniquement les familles de moteurs utilisées. Les identifiants Search Console couvrent les workflows de recherche principaux. GA4, CrUX et les workflows éligibles de l’API Indexing nécessitent leur propre configuration facultative.' },
        { question: 'Une soumission acceptée prouve-t-elle l’indexation ?', answer: "Non. Elle prouve uniquement que le moteur a accepté la demande. Mesurez séparément l’exploration et l’indexation lors d’un contrôle ultérieur comparable." },
        { question: 'Puis-je utiliser Search Console MCP avec Claude et Codex ?', answer: 'Oui. Search Console MCP fonctionne en stdio avec Claude, Codex et les autres clients MCP compatibles. Le chemin de l’exécutable et le format de configuration dépendent du client.' },
        { question: 'Où stocker les identifiants ?', answer: 'Conservez les identifiants dans l’environnement du serveur MCP ou dans la configuration du client. Le site public ne les reçoit jamais et les prompts ne doivent pas contenir de secrets.' },
      ],
    },
    final: { kicker: 'Commencez avec votre site.', title: 'Obtenez votre premier plan d’action SEO.', copy: 'Connectez vos comptes et laissez Claude ou Codex réaliser votre premier audit. Obtenez les corrections prioritaires pour améliorer votre visibilité.', button: 'Copier la commande uvx finale', guide: "Lire le guide d’installation" },
    footer: {
      tagline: 'Automatisez vos audits SEO. Améliorez votre visibilité avec l’IA.', creator: 'Ingénierie IA open source par', groups: { navigate: 'Navigation', product: 'Produit', ecosystem: 'Écosystème' },
      nav: [['Vue d’ensemble', '#main-content'], ['Choisir un problème', '#outcomes'], ['Moteurs', '#capabilities'], ['Workflow', '#workflow'], ['Installation', '#install'], ['Sécurité', '#safety'], ['FAQ', '#faq']],
      product: ['Documentation', 'GitHub', 'PyPI', "Guide d’installation", 'Historique', 'Licence MIT'], ecosystem: ['Tous les projets', 'Guide Claude Code', 'StarMapper', 'CCBoard', 'CC-Copilot Bridge', 'YT Insights'],
      creatorLinks: ['Portfolio', 'Blog', 'Profil GitHub', 'LinkedIn'], external: 'ouvre un nouvel onglet',
    },
  },
} as const
