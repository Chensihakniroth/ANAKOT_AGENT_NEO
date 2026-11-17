import type { ModelOptionProvider } from './types'

/**
 * A provider's unnamed preview SKU — free by naming convention, here today and gone tomorrow.
 * The convention is the codebase's own: `agent/credits_tracker.py::is_free_tier_model` and
 * `agent/auxiliary_client.py::_is_free_model` both treat a `stealth/` prefix as free.
 */
const STEALTH_PREFIX = 'stealth/'

/** Section id of the cross-provider stealth section. */
const STEALTH_ID = 'stealth'

export interface FreeModelEntry {
  model: string
  provider: ModelOptionProvider
}

export interface FreeModelGroup {
  entries: FreeModelEntry[]
  freeTier: boolean
  /** Section identity — `stealth`, or the owning provider's slug. Also the React key. */
  id: string
  /** Heading text. */
  label: string
  /** Provider slug shown beside the heading; empty for the stealth section, which spans providers. */
  slug: string
  stealth: boolean
}

/**
 * True for a `stealth/` preview SKU. Such a model carries no pricing row, so it is the naming
 * convention — not the catalog — that marks it free.
 */
export function isStealthModel(model: string): boolean {
  return model.trim().toLowerCase().startsWith(STEALTH_PREFIX)
}

export function isModelFree(provider: ModelOptionProvider, model: string): boolean {
  const pricing = provider.pricing?.[model]
  const normalized = model.toLowerCase()

  return Boolean(
    pricing?.free ||
      normalized.endsWith(':free') ||
      normalized.endsWith('-free') ||
      // Unpriced by design, so the tier partition parks a stealth SKU in `unavailable_models`. The
      // name is the only signal it has, and the codebase already trusts it everywhere else.
      isStealthModel(model) ||
      (provider.free_tier && !provider.unavailable_models?.includes(model))
  )
}

function entryMatches(entry: FreeModelEntry, terms: string[]): boolean {
  const providerText = `${entry.provider.name} ${entry.provider.slug}`.toLowerCase()
  const modelText = entry.model.toLowerCase()

  return terms.every(term => providerText.includes(term) || modelText.includes(term))
}

/**
 * Free models grouped for the page: one section per authenticated provider, preceded by a single
 * `Stealth` section holding every provider's preview SKUs — they are the same kind of thing whoever
 * happens to be serving them. Empty sections drop out, and a search filters within each section.
 */
export function filterFreeModelGroups(
  providers: readonly ModelOptionProvider[],
  search = '',
  stealthLabel = 'Stealth'
): FreeModelGroup[] {
  const query = search.trim().toLowerCase()
  const terms = query ? query.split(/\s+/) : []
  const stealth: FreeModelEntry[] = []
  const groups: FreeModelGroup[] = []

  for (const provider of providers) {
    if (provider.authenticated !== true) {
      continue
    }

    const entries = (provider.models ?? [])
      .filter(model => isModelFree(provider, model))
      .map(model => ({ model, provider }))

    if (!entries.length) {
      continue
    }

    const owned = entries.filter(entry => !isStealthModel(entry.model))

    stealth.push(...entries.filter(entry => isStealthModel(entry.model)))

    if (owned.length) {
      groups.push({
        entries: owned,
        freeTier: Boolean(provider.free_tier),
        id: provider.slug,
        label: provider.name,
        slug: provider.slug,
        stealth: false
      })
    }
  }

  const sections = stealth.length
    ? [
        { entries: stealth, freeTier: false, id: STEALTH_ID, label: stealthLabel, slug: '', stealth: true },
        ...groups
      ]
    : groups

  if (!terms.length) {
    return sections
  }

  return sections
    .map(section => ({ ...section, entries: section.entries.filter(entry => entryMatches(entry, terms)) }))
    .filter(section => section.entries.length > 0)
}

export function freeModelCount(groups: readonly FreeModelGroup[]): number {
  return groups.reduce((total, group) => total + group.entries.length, 0)
}
