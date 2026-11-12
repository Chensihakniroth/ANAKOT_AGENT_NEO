# Font Handling Reference

## Relative Path Resolution

Font paths in CSS are relative to the CSS file location, not the project root.

### Rule
- Count directory levels from the CSS file to the project root, then to the font location
- A path like ../../assets/... is relative to the CSS file's directory, not the project root

### Example
CSS: apps/desktop/src/components/onboarding/first-run/intro-copy.css
Font: apps/desktop/assets/fonts/SaintCarell.otf
Path: ../../../../assets/fonts/SaintCarell.otf

## Font File Formats

| Format | Use case | CSS format type |
|--------|----------|-----------------|
| .otf | Desktop app (Electron) | format('opentype') |
| .ttf | Desktop app (Electron) | format('truetype') |
| .woff2 | Web/React (Vite build) | format('woff2') |

## @font-face Setup Checklist

- [ ] Font file is in the project (not just downloaded)
- [ ] @font-face has font-family naming the family exactly
- [ ] src uses a relative path from the CSS file to the font
- [ ] font-display: swap
- [ ] font-family applied to the CSS selector that needs it
- [ ] Fallback chain includes system-ui, sans-serif

## Font Selection for Intro/Logo Text

- Distinctive typeface (same as the brand icon/logo)
- Applied to the intro copy text (not the chat body)
- Tested at small sizes (16-20px for the intro overlay)
- Paired with a fallback chain (Segoe WPC, Segoe UI, system-ui, sans-serif)
