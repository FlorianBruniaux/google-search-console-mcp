import { getSiteLinks, type Locale } from './content'

export interface NavigationLink { href: string; label: string; description: string; external?: boolean }
export interface NavigationGroup { label: string; links: NavigationLink[] }
export interface NavigationSection {
  id: 'analyze' | 'start' | 'resources'
  label: string
  description: string
  overview: { href: string; label: string; external?: boolean }
  groups: NavigationGroup[]
}

export function getNavigationSections(locale: Locale): NavigationSection[] {
  const links = getSiteLinks(locale)
  if (locale === 'fr') return [
    {
      id: 'analyze', label: 'Analyser', description: 'Partez de votre problème pour obtenir un diagnostic et des correctifs proposés par votre assistant IA.', overview: { href: '#outcomes', label: 'Choisir mon point d’entrée' },
      groups: [
        { label: 'Moteurs de recherche', links: [
          { href: '#provider-google', label: 'Données Google', description: 'Preuves Search Console, GA4 et CrUX.' },
          { href: '#provider-bing', label: 'Données Bing', description: 'Performances Webmaster, exploration et signaux de soumission.' },
          { href: '#provider-public', label: 'Analyse des pages publiques', description: 'Métadonnées, schema, sitemaps et liens internes.' },
        ] },
        { label: 'Workflow', links: [
          { href: '#outcomes', label: 'Choisir un problème', description: 'Débuter en SEO, comprendre une baisse ou améliorer sa visibilité : un prompt pour commencer.' },
          { href: '#real-example', label: 'Voir une analyse réelle', description: 'Mesures, constats, suggestions et logs sur cc.bruniaux.com.' },
          { href: '#workflow', label: 'Fonctionnement', description: 'Connecter, demander, analyser, corriger et mesurer.' },
          { href: '#safety', label: 'Limites des preuves', description: 'Séparer les états observés, calculés et demandés.' },
          { href: '#faq', label: 'FAQ', description: 'Réponses sur les moteurs et les identifiants.' },
        ] },
      ],
    },
    {
      id: 'start', label: 'Démarrer', description: 'Installez la configuration minimale utile, puis vérifiez chaque moteur séparément.', overview: { href: '#install', label: "Voir le parcours d’installation" },
      groups: [
        { label: 'Installation', links: [
          { href: '#install-evaluate', label: 'Évaluer une fois', description: 'Lancer le package avec uvx sans modifier le projet.' },
          { href: '#install-persistent', label: 'Installation durable', description: "Installer l’exécutable pour un usage MCP répété." },
          { href: '#install-verify', label: 'Vérifier les accès', description: 'Lister les propriétés et valider les moteurs indépendamment.' },
        ] },
        { label: 'Configurer les moteurs', links: [
          { href: links.googleSetup, label: 'Configuration Google', description: 'Configurer Search Console et les services Google facultatifs.' },
          { href: links.bingSetup, label: 'Configuration Bing', description: 'Configurer Webmaster Tools et IndexNow par hôte.' },
          { href: links.starterPrompts, label: 'Prompts de démarrage', description: 'Utiliser des prompts bornés pour les audits courants.' },
        ] },
      ],
    },
    {
      id: 'resources', label: 'Ressources', description: "Consultez le code source, l’historique et les contrats d’utilisation explicites.", overview: { href: links.repository, label: 'Ouvrir le dépôt', external: true },
      groups: [
        { label: 'Projet', links: [
          { href: links.repository, label: 'GitHub', description: 'Code source, issues et historique des contributions.', external: true },
          { href: links.pypi, label: 'PyPI', description: 'Package publié et métadonnées de version.', external: true },
          { href: links.updates, label: 'Nouveautés', description: 'Ajouts et correctifs datés, avec leur statut de publication.' },
          { href: links.sitemap, label: 'Plan du site', description: 'Toutes les pages regroupées par usage.' },
          { href: links.architecture, label: 'Architecture', description: 'Limites du serveur et structure des moteurs.' },
        ] },
        { label: 'Confiance et documentation', links: [
          { href: links.install, label: 'Installation', description: 'Configuration et vérification par client.' },
          { href: links.bingContract, label: 'Preuves et sécurité', description: "États, périmètres et limites d’écriture." },
          { href: links.license, label: 'Licence', description: 'Conditions de la licence MIT.' },
          { href: '#faq', label: 'FAQ', description: 'Identifiants, moteurs et sémantique des preuves.' },
        ] },
      ],
    },
  ]

  return [
    {
      id: 'analyze', label: 'Analyze', description: 'Start with your problem to get a diagnosis and suggested fixes from your AI assistant.', overview: { href: '#outcomes', label: 'Choose my starting point' },
      groups: [
        { label: 'Search providers', links: [
          { href: '#provider-google', label: 'Google data', description: 'Search Console, GA4 and CrUX evidence.' },
          { href: '#provider-bing', label: 'Bing data', description: 'Webmaster performance, crawl and submission signals.' },
          { href: '#provider-public', label: 'Public-page analysis', description: 'Metadata, schema, sitemaps and internal links.' },
        ] },
        { label: 'Workflow', links: [
          { href: '#outcomes', label: 'Choose a problem', description: 'Start with SEO, understand a traffic drop or improve visibility: a prompt to get started.' },
          { href: '#real-example', label: 'See a real analysis', description: 'Metrics, findings, suggestions and logs from cc.bruniaux.com.' },
          { href: '#workflow', label: 'How it works', description: 'Connect, ask, analyze, fix and measure.' },
          { href: '#safety', label: 'Evidence boundaries', description: 'Separate observed, derived and requested states.' },
          { href: '#faq', label: 'FAQ', description: 'Resolve common provider and credential questions.' },
        ] },
      ],
    },
    {
      id: 'start', label: 'Start', description: 'Install the smallest useful setup, then verify each provider separately.', overview: { href: '#install', label: 'See the installation path' },
      groups: [
        { label: 'Install', links: [
          { href: '#install-evaluate', label: 'Evaluate once', description: 'Run the package with uvx without changing a project.' },
          { href: '#install-persistent', label: 'Persistent install', description: 'Install the executable for repeat MCP use.' },
          { href: '#install-verify', label: 'Verify access', description: 'List properties and validate providers independently.' },
        ] },
        { label: 'Configure providers', links: [
          { href: links.googleSetup, label: 'Google setup', description: 'Configure Search Console and optional Google services.' },
          { href: links.bingSetup, label: 'Bing setup', description: 'Configure Webmaster Tools and host-scoped IndexNow.' },
          { href: links.starterPrompts, label: 'Starter prompts', description: 'Use bounded prompts for common audit workflows.' },
        ] },
      ],
    },
    {
      id: 'resources', label: 'Resources', description: 'Inspect the source, release history and explicit operating contracts.', overview: { href: links.repository, label: 'Open the repository', external: true },
      groups: [
        { label: 'Project', links: [
          { href: links.repository, label: 'GitHub', description: 'Source, issues and contribution history.', external: true },
          { href: links.pypi, label: 'PyPI', description: 'Published package and version metadata.', external: true },
          { href: links.updates, label: 'What’s new', description: 'Dated additions and fixes with their release status.' },
          { href: links.sitemap, label: 'Sitemap', description: 'Every page, grouped by use.' },
          { href: links.architecture, label: 'Architecture', description: 'Server boundaries and provider structure.' },
        ] },
        { label: 'Trust & documentation', links: [
          { href: links.install, label: 'Installation', description: 'Client-specific setup and verification.' },
          { href: links.bingContract, label: 'Evidence and safety', description: 'States, scopes and write boundaries.' },
          { href: links.license, label: 'License', description: 'MIT usage terms.' },
          { href: '#faq', label: 'FAQ', description: 'Credentials, providers and evidence semantics.' },
        ] },
      ],
    },
  ]
}
