import { skillCatalogInstallIdentifier } from '@anakot/shared'
import { queryOptions, useQuery } from '@tanstack/react-query'

import { CATALOG_ORIGIN } from '@/lib/plugin-catalog'
import { queryClient } from '@/lib/query-client'

import { curatedFeaturedRank, curationOwnsArtwork, officialCatalogArtwork } from './catalog-curation'

export type CatalogKind = 'skills' | 'plugins'

export interface CatalogEntry {
  id: string
  name: string
  description: string
  overview: string
  category: string
  categoryLabel: string
  source: string
  author: string
  identifier: string
  installIdentifier?: string | null
  repo: string
  sha: string
  subdir: string
  version: string
  requiresAnakot: string
  tags: string[]
  platforms: string[]
  requirements: string[]
  tools: string[]
  hooks: string[]
  middleware?: string[]
  commands?: string[]
  license?: string
  sourceUrl: string | null
  docsUrl: string | null
  /** Catalog-provided media, restricted to the same GitHub hosts as the website. */
  imageUrl: string | null
  screenshots?: string[]
  addedAt?: string
  /** Installed skill the user locked against agent edits. */
  locked?: boolean
  /** Installed skill's use count (skills only). */
  usage?: number
  /** Installed entry with a newer upstream version. */
  updateAvailable?: boolean
  updatedAt?: string
  stars: number | null
  /** 1-based curated hero rank from the catalog feed (`catalog-curation.json`). */
  featured?: number
  search: string
}

/**
 * Ordered hosts for the published snapshots (`<base>/skills.json`,
 * `<base>/plugins.json`). A rung is trusted only after it serves the file, so a
 * deployment going dark degrades to the next one instead of an error card: the
 * canonical docs domain fronts the static host, and the static host answers
 * directly when that front door breaks. Both send `Access-Control-Allow-Origin`
 * (a renderer fetch needs it), and both publish the same generator output.
 *
 * Do not "rebrand" a rung to a path that publishes nothing: this list once held
 * `nousresearch.github.io/anakot-agent/docs/api`, which 404s, and every new
 * install got "Catalog HTTP 404" on Skills and Plugins. Adding a rung is cheap;
 * a rung that cannot serve data is not a rung.
 */
const CATALOG_HOSTS = [
  'https://hermes-agent.nousresearch.com/docs/api',
  'https://nousresearch.github.io/hermes-agent/docs/api'
] as const

/** A download with no new bytes for this long is aborted (inactivity, not total time). */
const CATALOG_STALL_MS = 60_000
const text = (value: unknown): string => (typeof value === 'string' ? value : '')
const strings = (value: unknown): string[] => (Array.isArray(value) ? value.filter(v => typeof v === 'string') : [])

const IMAGE_HOSTS = new Set(['raw.githubusercontent.com', 'github.com'])

// URL.parse, not `new URL` in try/catch: most skill rows carry no repo or docs
// URL, and 200k thrown TypeErrors cost ~0.7s of main thread per catalog load.
const parseUrl = (value: unknown) => URL.parse(text(value))

/** Mirrors scripts/validate_plugin_catalog.py: https on a GitHub host, else no image. */
export function catalogImageUrl(value: unknown): string | null {
  const url = parseUrl(value)
  const host = url?.hostname.toLowerCase() ?? ''

  return url?.protocol === 'https:' && (IMAGE_HOSTS.has(host) || host.endsWith('.githubusercontent.com'))
    ? url.href
    : null
}

function webUrl(value: unknown): string | null {
  const url = parseUrl(value)

  return url?.protocol === 'https:' || url?.protocol === 'http:' ? url.href : null
}

/** Display form of a source or category id: domains stay verbatim (`browse.sh`),
 *  slugs read as words (`software-development` → `Software Development`). */
export const catalogLabel = (value: string) =>
  value.includes('.') ? value : value.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

const isoDate = (value: unknown) => (Number.isFinite(Date.parse(text(value))) ? text(value) : undefined)

/** Where an entry points: install id, source/docs links, artwork. */
function catalogLinks(kind: CatalogKind, row: any, rawName: string, source: string) {
  return {
    installIdentifier:
      kind === 'skills'
        ? skillCatalogInstallIdentifier({
            name: rawName,
            source,
            identifier: text(row.identifier),
            installIdentifier: text(row.installIdentifier)
          })
        : null,
    sourceUrl: webUrl(row.repo || row.sourceUrl),
    docsUrl:
      webUrl(row.docsUrl) || (text(row.docsPath) ? `${CATALOG_ORIGIN}/docs/user-guide/skills/${text(row.docsPath)}` : null),
    imageUrl: curationOwnsArtwork(kind, row) ? officialCatalogArtwork(kind, row) : catalogImageUrl(row.image),
    screenshots:
      kind === 'plugins'
        ? strings(row.screenshots)
            .map(catalogImageUrl)
            .filter((url): url is string => url !== null)
        : []
  }
}

/** Ranking signals: dates, stars, curated rank. */
function catalogSignals(kind: CatalogKind, row: any) {
  return {
    addedAt: isoDate(row.addedAt),
    updatedAt: isoDate(row.updatedAt),
    stars: typeof row.stars === 'number' && Number.isFinite(row.stars) ? row.stars : null,
    featured: typeof row.featured === 'number' && row.featured > 0 ? row.featured : curatedFeaturedRank(kind, row)
  }
}

function catalogEntry(kind: CatalogKind, row: any): CatalogEntry {
  const rawName = text(row.name)
  // Registry rows occasionally carry a stray front-matter delimiter ("---")
  // as their name; show the slug instead of a blank title.
  const name = /[\p{L}\p{N}]/u.test(rawName) ? rawName : text(row.identifier) || rawName
  const source = text(kind === 'plugins' ? row.tier : row.source)
  const identifier = text(row.identifier) || rawName
  const caps = row.capabilities ?? {}
  const category = text(row.category) || 'uncategorized'
  const categoryLabel = text(row.categoryLabel) || category
  const tags = strings(row.tags)
  const tools = strings(caps.providesTools)
  const hooks = strings(caps.providesHooks)
  const middleware = strings(caps.providesMiddleware)
  const commands = strings(row.commands)
  const platforms = strings(row.platforms)
  const requirements = strings(kind === 'plugins' ? caps.requiresEnv : row.envVars)
  const author = text(row.maintainer ?? row.author)
  const description = text(row.description)

  return {
    id: `${source}:${identifier}`,
    name,
    description,
    overview: text(row.overview),
    category,
    categoryLabel,
    source,
    author,
    identifier,
    repo: text(row.repo),
    sha: text(row.sha),
    subdir: text(row.subdir),
    version: text(row.version),
    requiresAnakot: text(row.requiresAnakot),
    tags,
    tools,
    hooks,
    middleware,
    commands,
    license: text(row.license) || undefined,
    platforms,
    requirements,
    ...catalogLinks(kind, row, rawName, source),
    ...catalogSignals(kind, row),
    search: [
      name,
      description,
      text(row.overview),
      author,
      category,
      categoryLabel,
      source,
      ...tags,
      ...tools,
      ...hooks,
      ...platforms,
      ...requirements,
      ...commands,
      ...middleware
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
  }
}

export function parseCatalog(kind: CatalogKind, data: unknown): CatalogEntry[] {
  if (!Array.isArray(data)) {
    throw new Error('Invalid catalog response')
  }

  const entries = new Map<string, CatalogEntry>()

  for (const row of data) {
    if (row && typeof row === 'object' && text(row.name)) {
      const entry = catalogEntry(kind, row)

      entries.set(entry.id, entry)
    }
  }

  return [...entries.values()]
}

/** A host that cannot serve the snapshot hands the ladder a reason, never a retry loop. */
type CatalogAttempt = { entries: CatalogEntry[] } | { unavailable: string }

export async function fetchCatalog(kind: CatalogKind): Promise<CatalogEntry[]> {
  let unavailable = ''

  for (const host of CATALOG_HOSTS) {
    const attempt = await downloadCatalog(kind, `${host}/${kind}.json`)

    if ('entries' in attempt) {
      return attempt.entries
    }

    unavailable = attempt.unavailable
  }

  throw new Error(unavailable)
}

async function downloadCatalog(kind: CatalogKind, url: string): Promise<CatalogAttempt> {
  // Bound inactivity, not total transfer time: a large skills snapshot can
  // take minutes on a healthy slow connection. Headers and each body chunk
  // get the same deadline; an actually stalled download still terminates.
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined

  const armDeadline = () => {
    clearTimeout(timer)
    timer = setTimeout(() => controller.abort(), CATALOG_STALL_MS)
  }

  armDeadline()

  try {
    let response: Response

    try {
      response = await fetch(url, {
        credentials: 'omit',
        signal: controller.signal
      })
    } catch (error) {
      // A stall says nothing about the host, and retrying a 66 MB snapshot on
      // the next rung would double the wait the user already sat through.
      if (controller.signal.aborted) {
        throw error
      }

      // Unreachable / CORS-blocked / DNS: this host has no verdict to give.
      return { unavailable: `Catalog host unreachable: ${url}` }
    }

    if (!response.ok) {
      return { unavailable: `Catalog HTTP ${response.status}` }
    }

    if (!response.body) {
      return { entries: parseCatalog(kind, await response.json()) }
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    const chunks: string[] = []
    armDeadline()

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        if (value.byteLength > 0) {
          armDeadline()
        }

        chunks.push(decoder.decode(value, { stream: true }))
      }
    } finally {
      reader.releaseLock()
    }

    clearTimeout(timer)
    chunks.push(decoder.decode())

    return { entries: parseCatalog(kind, JSON.parse(chunks.join(''))) }
  } catch (error) {
    // Chromium can turn our abort into "The user aborted a request." The
    // controller, not that browser-dependent exception name, owns the cause.
    if (controller.signal.aborted) {
      throw new Error(`Catalog download timed out after ${CATALOG_STALL_MS / 1000} seconds without progress. Please try again.`)
    }

    throw error
  } finally {
    clearTimeout(timer)
  }
}

const catalogQuery = (kind: CatalogKind) =>
  queryOptions({
    queryKey: ['public-catalog', kind],
    queryFn: () => fetchCatalog(kind),
    staleTime: 30 * 60_000,
    // The skills snapshot parses to ~100k rows; release it once the page has
    // been left long enough that a revisit is a fresh browse anyway.
    gcTime: 30 * 60_000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    retryOnMount: false,
    retry: false
  })

export function useCatalog(kind: CatalogKind) {
  return useQuery({
    ...catalogQuery(kind),
    // A failed catalog stays parked across remounts (tab switches) until the
    // user explicitly chooses Try again.
    enabled: query => query.state.status !== 'error'
  })
}

/** Warm a catalog while the browser is idle so switching tabs doesn't pay the fetch + parse. */
export function prefetchCatalogWhenIdle(kind: CatalogKind) {
  const id = requestIdleCallback(() => void queryClient.prefetchQuery(catalogQuery(kind)), { timeout: 5_000 })

  return () => cancelIdleCallback(id)
}
