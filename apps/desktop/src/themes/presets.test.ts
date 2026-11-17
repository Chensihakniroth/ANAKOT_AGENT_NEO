import { contrastRatio } from '@anakot/shared/color'
import { describe, expect, it } from 'vitest'

import {
  BUILTIN_THEME_LIST,
  BUILTIN_THEMES,
  DEFAULT_SKIN_NAME,
  DEFAULT_TYPOGRAPHY,
  evaTheme,
  nousTheme
} from './presets'

// #40364: none of the UI text/mono fonts carry emoji glyphs, so every font
// stack must end with a color-emoji fallback or emoji render as tofu on
// platforms whose default font lacks them (e.g. Linux).
describe('theme typography emoji fallback (#40364)', () => {
  const stacks: Array<[string, string]> = [
    ['DEFAULT_TYPOGRAPHY.fontSans', DEFAULT_TYPOGRAPHY.fontSans],
    ['DEFAULT_TYPOGRAPHY.fontMono', DEFAULT_TYPOGRAPHY.fontMono],
    // A theme may override only fontMono (fontSans then falls back to the
    // default, which already carries the emoji stack), so skip undefined.
    ...BUILTIN_THEME_LIST.flatMap(theme =>
      (
        [
          [`${theme.name}.fontSans`, theme.typography?.fontSans],
          [`${theme.name}.fontMono`, theme.typography?.fontMono]
        ] as Array<[string, string | undefined]>
      ).filter((entry): entry is [string, string] => typeof entry[1] === 'string')
    )
  ]

  it.each(stacks)('%s includes a color-emoji font', (_label, stack) => {
    expect(stack).toMatch(/Apple Color Emoji|Segoe UI Emoji|Noto Color Emoji|(^|,\s*)emoji\b/)
  })
})

describe('theme typography Latin Extended fallback (#61392)', () => {
  const monoStacks: Array<[string, string]> = [
    ['DEFAULT_TYPOGRAPHY.fontMono', DEFAULT_TYPOGRAPHY.fontMono],
    ...BUILTIN_THEME_LIST.map(
      theme =>
        [
          `${theme.name}.effectiveFontMono`,
          theme.typography?.fontMono ?? nousTheme.typography?.fontMono ?? DEFAULT_TYPOGRAPHY.fontMono
        ] as [string, string]
    )
  ]

  it.each(monoStacks)('%s falls back to bundled JetBrains Mono before generic fonts', (_label, stack) => {
    const jetbrains = stack.indexOf('JetBrains Mono')

    expect(jetbrains).toBeGreaterThanOrEqual(0)

    const genericIndexes = [
      stack.indexOf('ui-monospace'),
      stack.indexOf('monospace'),
      stack.indexOf('Apple Color Emoji'),
      stack.indexOf('Segoe UI Emoji'),
      stack.indexOf('Noto Color Emoji')
    ].filter(index => index >= 0)

    expect(genericIndexes.length).toBeGreaterThan(0)
    expect(jetbrains).toBeLessThan(Math.min(...genericIndexes))
  })

  it('default stack includes common Linux monospace glyph fallbacks', () => {
    expect(DEFAULT_TYPOGRAPHY.fontMono).toContain('DejaVu Sans Mono')
    expect(DEFAULT_TYPOGRAPHY.fontMono).toContain('Liberation Mono')
    expect(DEFAULT_TYPOGRAPHY.fontMono).toContain('Noto Sans Mono')
  })
})

// EVA-01 is the fork's identity: the skin a stock install opens on, and still a
// preset a user can switch to (and away from). Both halves are load-bearing —
// dropping it from BUILTIN_THEMES would make the default unreachable, and
// un-defaulting it silently hands every user upstream's white/blue.
describe('EVA-01 is the shipped identity and a switchable preset', () => {
  it('is the default skin, registered under that same name', () => {
    expect(DEFAULT_SKIN_NAME).toBe('eva')
    expect(BUILTIN_THEMES[DEFAULT_SKIN_NAME]).toBe(evaTheme)
    expect(evaTheme.label).toBe('EVA-01')
    expect(BUILTIN_THEME_LIST.some(theme => theme.name === DEFAULT_SKIN_NAME)).toBe(true)
  })

  it('ships a distinct palette per appearance, both EVA — only the mode changes', () => {
    // `paletteFor` synthesises a pale variant FROM the dark palette when
    // darkColors is absent, which would drift off-brand; both ends are explicit.
    expect(evaTheme.darkColors).not.toBe(evaTheme.colors)
    expect(evaTheme.colors.background.toLowerCase()).toBe('#f5eef8')
    expect(evaTheme.darkColors!.background.toLowerCase()).toBe('#402d59')

    // And neither end is the stock white/blue the fork replaced.
    for (const mode of [evaTheme.colors, evaTheme.darkColors!]) {
      expect(mode.background.toLowerCase()).not.toBe('#ffffff')
      expect([mode.primary.toLowerCase(), (mode.midground ?? '').toLowerCase()]).not.toContain('#0053fd')
    }
  })

  it('clears WCAG AA on every pair the shell paints, in BOTH appearances', () => {
    const appearances = [
      ['light', evaTheme.colors],
      ['dark', evaTheme.darkColors!]
    ] as const

    for (const [modeName, c] of appearances) {
      const pairs: Array<[string, string, number, string]> = [
        [c.foreground, c.background, 7, 'body text'],
        [c.foreground, c.card, 7, 'text on cards'],
        [c.foreground, c.sidebarBackground!, 7, 'sidebar text'],
        [c.foreground, c.userBubble!, 7, 'text in your own bubble'],
        [c.mutedForeground, c.background, 4.5, 'secondary text'],
        [c.primaryForeground, c.primary, 4.5, 'ink on the primary button'],
        [c.secondaryForeground, c.secondary, 4.5, 'ink on purple'],
        [c.midground!, c.background, 4.5, 'neon accent as text'],
        [c.destructiveForeground, c.destructive, 4.5, 'ink on danger']
      ]

      for (const [fg, bg, min, label] of pairs) {
        expect(contrastRatio(fg, bg), `${modeName}: ${label}`).toBeGreaterThanOrEqual(min)
      }
    }
  })
})
