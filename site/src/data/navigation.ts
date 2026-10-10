import { getSiteLinks, type Locale } from './content'
import { getProfiles } from './journeys'

export interface NavigationLink { href: string; label: string; description: string; external?: boolean }
export interface NavigationGroup { label: string; links: NavigationLink[] }
export interface NavigationSection {
  id: 'analyze' | 'start' | 'resources'
  label: string
  description: string
  overview: { href: string; label: string; external?: boolean }
  groups: NavigationGroup[]
}

function getJourneyNavigation(locale: Locale): NavigationSection {
  const fr = locale === 'fr'
  const links = getSiteLinks(locale)
  return {
    id: 'start', label: fr ? 'Votre parcours' : 'Your path',
    description: fr ? 'Choisissez votre métier. Chaque parcours propose un démarrage guidé et les détails des contrôles.' : 'Choose your role. Each path includes guided setup and detailed checks.',
    overview: { href: '#personas', label: fr ? 'Comparer les parcours' : 'Compare the paths' },
    groups: [
      { label: fr ? 'Par métier' : 'By role', links: getProfiles(locale).map((profile) => ({ href: profile.href, label: profile.label, description: profile.intro })) },
      { label: fr ? 'Accès directs' : 'Direct access', links: [
        { href: links.install, label: fr ? 'Installation guidée' : 'Guided installation', description: fr ? 'Découvrir MCP quel que soit votre niveau SEO.' : 'Get started with MCP at any SEO experience level.' },
        { href: links.tools, label: fr ? 'Catalogue des outils' : 'Tool catalogue', description: fr ? 'Familles, paramètres et contrats du serveur.' : 'Families, parameters and server contracts.' },
        { href: links.starterPrompts, label: fr ? 'Prompts et premiers tests' : 'Prompts and first tests', description: fr ? 'Demandes bornées et test sans compte Google ou Bing.' : 'Bounded requests and a test without Google or Bing accounts.' },
      ] },
    ],
  }
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
    getJourneyNavigation(locale),
    {
      id: 'resources', label: 'Ressources', description: "Consultez le code source, l’historique et les contrats d’utilisation explicites.", overview: { href: links.repository, label: 'Ouvrir le dépôt', external: true },
      groups: [
        { label: 'Projet', links: [
          { href: links.repository, label: 'GitHub', description: 'Code source, issues et historique des contributions.', external: true },
          { href: links.pypi, label: 'PyPI', description: 'Package publié et métadonnées de version.', external: true },
          { href: links.updates, label: 'Nouveautés', description: 'Ajouts et correctifs datés, avec leur statut de publication.' },
          { href: links.sitemap, label: 'Plan du site', description: 'Toutes les pages regroupées par usage.' },
          { href: links.architecture, label: 'Architecture', description: 'Limites du serveur et structure des moteurs.' },
          { href: links.nativeAudit, label: 'Audit natif depuis les sources', description: 'Workflow non publié : profils explicites, budgets et limites des preuves.' },
        ] },
        { label: 'Confiance et documentation', links: [
          { href: links.install, label: 'Installation', description: 'Configuration et vérification par client.' },
          { href: links.googleSetup, label: 'Configuration Google', description: 'Accès Search Console et sources Google facultatives.' },
          { href: links.bingSetup, label: 'Configuration Bing', description: 'Accès Webmaster Tools et distinction avec IndexNow.' },
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
    getJourneyNavigation(locale),
    {
      id: 'resources', label: 'Resources', description: 'Inspect the source, release history and explicit operating contracts.', overview: { href: links.repository, label: 'Open the repository', external: true },
      groups: [
        { label: 'Project', links: [
          { href: links.repository, label: 'GitHub', description: 'Source, issues and contribution history.', external: true },
          { href: links.pypi, label: 'PyPI', description: 'Published package and version metadata.', external: true },
          { href: links.updates, label: 'What’s new', description: 'Dated additions and fixes with their release status.' },
          { href: links.sitemap, label: 'Sitemap', description: 'Every page, grouped by use.' },
          { href: links.architecture, label: 'Architecture', description: 'Server boundaries and provider structure.' },
          { href: links.nativeAudit, label: 'Native audit from source', description: 'Unreleased workflow: explicit roles, budgets and evidence boundaries.' },
        ] },
        { label: 'Trust & documentation', links: [
          { href: links.install, label: 'Installation', description: 'Client-specific setup and verification.' },
          { href: links.googleSetup, label: 'Google setup', description: 'Search Console access and optional Google sources.' },
          { href: links.bingSetup, label: 'Bing setup', description: 'Webmaster Tools access and distinction from IndexNow.' },
          { href: links.bingContract, label: 'Evidence and safety', description: 'States, scopes and write boundaries.' },
          { href: links.license, label: 'License', description: 'MIT usage terms.' },
          { href: '#faq', label: 'FAQ', description: 'Credentials, providers and evidence semantics.' },
        ] },
      ],
    },
  ]
}
