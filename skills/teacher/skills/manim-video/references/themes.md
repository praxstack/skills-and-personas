# Themes: one registry, thirty looks, every kit

A film's colours come from one of two places:

- **`original`** (the default): the kit's own shipped palette, exactly as the starter film was verified.
- **A registry theme**: one of 30 themes in `scripts/themes.json`. There are ten families, and each has a light, a mid (in between) and a dark slot.

| Family | light | mid | dark |
|---|---|---|---|
| Pastel (this repo's own) | `pastel-cream` | `pastel-lavender` | `pastel-night` |
| Tokyo Night | `tokyonight-day` | `tokyonight-storm` | `tokyonight-night` |
| Catppuccin | `catppuccin-latte` | `catppuccin-macchiato` | `catppuccin-mocha` |
| Rosé Pine | `rosepine-dawn` | `rosepine-moon` | `rosepine-main` |
| Nord | `nord-snow` | `nord-frost` | `nord-polar` |
| Gruvbox | `gruvbox-light` | `gruvbox-soft` | `gruvbox-hard` |
| Everforest | `everforest-light` | `everforest-medium` | `everforest-hard` |
| Kanagawa | `kanagawa-lotus` | `kanagawa-wave` | `kanagawa-dragon` |
| GitHub | `github-light` | `github-dimmed` | `github-dark` |
| Ayu | `ayu-light` | `ayu-mirage` | `ayu-dark` |

Run `python3 scripts/theme.py list` for the same list with each theme's tone. Run `python3 scripts/theme.py show <id>` to see its colours and contrast table.

## Picking one

- If the brief's Style section names a theme, use it. If it names none, keep `original`.
- If the brief says "light", "pastel" or "dark" without a family, pick that slot of Catppuccin or Pastel, and say which one you picked in the brief.
- Record it with `python3 scripts/vstate.py set theme=<id>`.
- The brief gate rejects an unknown id. The visuals gate fails until the scene code reads a theme file emitted for that id from the current registry.

## Why the text colours differ from the upstream palette

Shipped editor palettes are made for code on a screen at arm's length. They are not made for a 1080p video frame, and 82 of their text colours miss our 4.5:1 rule. For example, Tokyo Night Day's orange is 3.6:1 on its own background.

`theme.py` keeps every **fill** as shipped: shapes, bars, glows, chapter lights. It **solves an ink** for text by keeping the same hue and saturation and moving the lightness away from the background until the colour clears its target on every surface (`bg`, `bg2`, `deep`, `panel`, `panel2`).

| Token | Target |
|---|---|
| `text` | 7:1, and 4.6:1 at 0.8 opacity (stepped back) |
| `muted` | 5.5:1 |
| `dim` | 4.6:1 |
| `<hue>Ink` | 4.6:1 |
| `on<Hue>` | 4.6:1 on that fill |

The order `text > muted > dim` always holds. `theme.py check` proves every target for all 30 themes, and CI runs it.

## Tokens (same keys in every format)

- **Surfaces:** `bg`, `bg2` (gradient partner), `deep` (shade under chapter cards), `panel`, `panel2`, `line`, `line2`.
- **Text:** `text`, `muted`, `dim`. Step back only `text`-coloured things; `muted` and `dim` are already the quiet colours.
- **Fills:** `accent`, `warm`, `good`, `bad`, `cool`, `gold`, `violet`. Use them for areas and thick strokes, **never for text**.
- **Inks:** `accentInk` … `violetInk`. Use them for text and thin strokes in a hue.
- **On-fills:** `onAccent` … `onViolet`. Use them for a label sitting on a filled shape of that hue.
- **Meta:**
  - `tone` (`light` or `dark`), `slot`, `name`, `family`, `source`
  - `lights` (six chapter key lights)
  - `shadow` (black on dark themes, a deep tint of the text colour on light ones)

## Emitting

```
python3 scripts/theme.py emit <id> --format <fmt> --out <path>
```

Formats:

- `js` / `ts` (ES module, `export const THEME`)
- `global` (`window.THEME = …`, for plain script tags)
- `css` (`:root { --t-bg: … }`)
- `py` (`THEME = {…}`)
- `json`

The file carries a `theme-id: <id>  sha: <fingerprint>` line, which is how the visuals gate knows the scene code reads the current theme. Re-emit it after anyone changes `themes.json`.

## What a kit must do on a light theme

The kits were built dark-first, so a light theme also flips these:

- **Grain and paper texture:** multiply or darken on light grounds; screen or lighten on dark ones. Keep the strength low.
- **Glows:** a glow on a light ground reads as a smudge. Use a soft shadow (`shadow` at low alpha) or a tinted fill instead.
- **Vignettes:** darken toward `deep` on dark themes; on light themes, use a gentle `deep` edge, never black.
- **Chapter cards:** cards use `panel` with `text`. The full-screen shade under them uses `deep`.
- **Code blocks:** code sits on `panel`. Syntax colours are inks, never fills.

Each kit's guide has a **Themes** section that names its theme file and its mapping from kit roles to tokens.

## Checking a theme

Render the review stills in the theme and run `legibility.py`, exactly as for the original palette: 26 px and 4.5:1 for every text, with no tolerance. The solved inks pass on flat surfaces by construction. What still breaks is text over gradients, glows, images and other text, and the stills catch that.
