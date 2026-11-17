'use client'

import { useState } from 'react'

import { AccentSwatch } from '@/components/ui/accent-swatch'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n'
import { useTheme } from '@/themes'
import { accentsFor, CUSTOM_ACCENT_PREFIX, NOUS_ACCENT } from '@/themes/accents'

import { CARD_ACTION_CLASS } from '../setup-beat/card-type'

import { useLookPreview } from './look-preview'

export interface AccentPickerCardProps {
  /** Answers with a swatch id, `custom:#rrggbb`, or null for the live theme's own accent; true once sent. */
  onContinue: (accent: null | string) => boolean
}

/** The theme's own accent, the eight swatches and a custom colour well; a click previews the accent, Continue answers with it. */
export function AccentPickerCard({ onContinue }: AccentPickerCardProps) {
  const { t } = useI18n()
  const { renderedMode, theme } = useTheme()
  const [custom, setCustom] = useState<null | string>(null)
  const look = useLookPreview('accent', renderedMode === 'dark')
  const staged = look.staged

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2.5 p-1" role="group">
        {/* The reset is its own swatch. It used to be the "Nous blue" entry, which
            only held while the default skin's accent WAS Nous blue — with EVA-01
            the default it would have painted green from a blue chip. */}
        <AccentSwatch
          active={staged?.value === null}
          hex={theme.colors.midground ?? theme.colors.primary}
          name={t.assistant.themePicker.themeAccent}
          onPick={() => look.stage(null)}
        />
        {accentsFor(renderedMode === 'dark').map(swatch => (
          <AccentSwatch
            active={staged?.value === swatch.id}
            hex={swatch.hex}
            key={swatch.id}
            name={swatch.name}
            onPick={() => look.stage(swatch.id)}
          />
        ))}
        <AccentSwatch
          active={custom !== null && staged?.value === `${CUSTOM_ACCENT_PREFIX}${custom}`}
          hex={custom ?? NOUS_ACCENT}
          name={t.assistant.themePicker.customColor}
          onColorChange={hex => {
            const value = hex.toLowerCase()

            setCustom(value)
            look.stage(`${CUSTOM_ACCENT_PREFIX}${value}`)
          }}
        />
      </div>
      <div>
        <Button className={CARD_ACTION_CLASS} disabled={!staged} onClick={() => look.commit(onContinue)} size="sm">
          {t.common.continue}
        </Button>
      </div>
    </div>
  )
}
