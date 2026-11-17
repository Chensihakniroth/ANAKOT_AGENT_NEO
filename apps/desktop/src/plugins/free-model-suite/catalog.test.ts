import { describe, expect, it } from 'vitest'

import { filterFreeModelGroups, freeModelCount, isModelFree, isStealthModel } from './catalog'
import type { ModelOptionProvider } from './types'

function provider(overrides: Partial<ModelOptionProvider> = {}): ModelOptionProvider {
  return {
    authenticated: true,
    models: [],
    name: 'Provider',
    slug: 'provider',
    ...overrides
  }
}

describe('free-model classification', () => {
  it('accepts explicit free pricing and naming markers', () => {
    expect(isModelFree(provider({ pricing: { m: { input: 'free', output: 'free', free: true } } }), 'm')).toBe(true)
    expect(isModelFree(provider(), 'vendor/model:free')).toBe(true)
    expect(isModelFree(provider(), 'vendor/model-free')).toBe(true)
  })

  it('does not treat a paid provider as making all of its models free', () => {
    expect(isModelFree(provider(), 'vendor/model')).toBe(false)
  })

  it('uses free-tier availability without including models the tier cannot select', () => {
    expect(isModelFree(provider({ free_tier: true, models: ['usable'] }), 'usable')).toBe(true)
    expect(
      isModelFree(provider({ free_tier: true, unavailable_models: ['locked'], models: ['locked'] }), 'locked')
    ).toBe(false)
  })

  it('treats a stealth/ preview SKU as free even though it is unpriced and parked as unavailable', () => {
    // An unpriced SKU lands in `unavailable_models` via the tier partition. The naming convention is
    // the only signal left, and the agent's own free-SKU checks (`agent/credits_tracker.py`,
    // `agent/auxiliary_client.py`) already trust it.
    const nous = provider({
      free_tier: true,
      models: ['stealth/space-bunny-alpha'],
      unavailable_models: ['stealth/space-bunny-alpha']
    })

    expect(isStealthModel('stealth/space-bunny-alpha')).toBe(true)
    expect(isStealthModel('Stealth/SPACE-BUNNY-ALPHA')).toBe(true)
    expect(isStealthModel('nightshade/stealth-thing')).toBe(false)
    expect(isModelFree(nous, 'stealth/space-bunny-alpha')).toBe(true)
  })
})

describe('catalog filtering', () => {
  it('keeps authenticated provider groups, removes empty ones, and searches model/provider names', () => {
    const groups = filterFreeModelGroups(
      [
        provider({
          models: ['alpha:free', 'paid'],
          pricing: { 'alpha:free': { input: 'free', output: 'free', free: true } }
        }),
        provider({ name: 'Hidden', slug: 'hidden', authenticated: false, models: ['hidden:free'] }),
        provider({ name: 'OpenRouter', slug: 'openrouter', models: ['vendor/beta:free', 'vendor/paid'] })
      ],
      'openrouter beta'
    )

    expect(groups).toHaveLength(1)
    expect(groups[0]).toMatchObject({ id: 'openrouter', slug: 'openrouter', stealth: false })
    expect(groups[0].entries.map(entry => entry.model)).toEqual(['vendor/beta:free'])
    expect(groups[0].entries[0].provider.slug).toBe('openrouter')
  })

  it('pulls stealth SKUs out of their provider into one leading section', () => {
    const groups = filterFreeModelGroups(
      [
        provider({
          name: 'Nous Portal',
          slug: 'nous',
          free_tier: true,
          models: ['openai/gpt-6-astra', 'stealth/one']
        }),
        provider({ name: 'OpenRouter', slug: 'openrouter', models: ['vendor/x:free', 'stealth/two'] })
      ],
      '',
      'Stealth'
    )

    expect(groups.map(group => group.id)).toEqual(['stealth', 'nous', 'openrouter'])
    expect(groups[0]).toMatchObject({ label: 'Stealth', slug: '', stealth: true })
    expect(groups[0].entries.map(entry => entry.model)).toEqual(['stealth/one', 'stealth/two'])
    // a stealth row still carries whichever provider must serve it, across providers
    expect(groups[0].entries.map(entry => entry.provider.slug)).toEqual(['nous', 'openrouter'])
    // and it is not duplicated into its provider's own section
    expect(groups[1].entries.map(entry => entry.model)).toEqual(['openai/gpt-6-astra'])
    expect(groups[2].entries.map(entry => entry.model)).toEqual(['vendor/x:free'])
  })

  it('omits the stealth section when no provider offers one', () => {
    const groups = filterFreeModelGroups([provider({ models: ['vendor/x:free'] })], '', 'Stealth')

    expect(groups.map(group => group.id)).toEqual(['provider'])
    expect(groups.some(group => group.stealth)).toBe(false)
  })

  it('drops a stealth section a search empties, and counts what survives', () => {
    const groups = filterFreeModelGroups(
      [provider({ slug: 'nous', models: ['stealth/one', 'vendor/y:free'] })],
      'vendor/y',
      'Stealth'
    )

    expect(groups.map(group => group.id)).toEqual(['nous'])
    expect(freeModelCount(groups)).toBe(1)
  })
})
