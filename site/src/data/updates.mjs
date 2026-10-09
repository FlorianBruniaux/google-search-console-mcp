// Dates belong to the source history, never to the time of the site build.
export function latestUpdate(changelog) {
  const unreleased = changelog.match(/^## \[Unreleased\][^\S\n]*\n([\s\S]*?)(?=^## |(?![\s\S]))/m)?.[1]
  const updated = unreleased?.match(/<!-- unreleased-updated: (\d{4}-\d{2}-\d{2}) -->/)?.[1]
  if (unreleased && /^- /m.test(unreleased)) {
    if (!updated || new Date(`${updated}T00:00:00Z`).toISOString().slice(0, 10) !== updated) {
      throw new Error('A nonempty Unreleased section requires a valid unreleased-updated date.')
    }
    return { date: updated, version: null, published: false }
  }
  const release = changelog.match(/^## \[([^\]]+)\] - (\d{4}-\d{2}-\d{2})/m)
  if (!release) throw new Error('The changelog has no dated release.')
  return { date: release[2], version: release[1], published: true }
}

export function formatUpdateDate(date, locale) {
  return new Intl.DateTimeFormat(locale === 'fr' ? 'fr-FR' : 'en-GB', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(`${date}T00:00:00Z`))
}
