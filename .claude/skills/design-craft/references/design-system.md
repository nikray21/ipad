# Working with a design system

A design system (brand tokens, fonts, components, existing product mocks) is a
*binding constraint*, not a suggestion. When one is provided, its rules win over
every default in this skill. The skill teaches craft; the system supplies the
specifics.

## The rule

When a design system is attached, **do not invent** colors, type, spacing, or
components that aren't grounded in it. Explore it, extract what you need, and
compose from its parts.

## How to use one well

1. **Read it first.** Find the index/README, the stylesheet(s), the token
   definitions, the component library, and any existing product mocks. Don't
   guess token names — look up the exact `--*` custom-property names in the
   actual CSS; an unresolved `var()` silently falls back to browser defaults.
2. **Copy, don't reference.** Bring the fonts, tokens, and components you need
   into your project as real copies. Don't hotlink into the system folder.
3. **Fork existing mocks.** If the system has a mock of a product like the one
   you're building, copy and adapt it — that's the fastest path to on-brand,
   high-quality output.
4. **Follow the existing vocabulary.** When extending an existing UI, match its
   copywriting tone, color usage, hover/active states, animation style, shadow/
   card/border patterns, and density. New elements should look like they were
   always there.
5. **Extend, don't contradict.** If you must introduce a value the system lacks
   (a new tint, an intermediate size), derive it *from* the system — hold the
   accent's hue and adjust lightness in OKLCH, use the existing spacing scale —
   rather than inventing a foreign value.

## If the system is thin or absent

The skill's defaults (OKLCH palettes, modular type scale, spacing unit, motion
curves) are your fallback. But the moment real tokens exist, they override the
fallback. Leave a clearly marked token block at the top of the build so a real
system can be dropped in later:

```css
:root {
  /* === BRAND TOKENS — replace with your design system === */
  --font-display: 'YourDisplay', serif;
  --font-body:    'YourBody', sans-serif;
  --accent:       oklch(0.58 0.18 255);
  --bg:           oklch(0.99 0.005 95);
  --text:         oklch(0.22 0.02 260);
  /* spacing, radius, shadows, motion curves… */
}
```

## Scope caution

A design system is a *visual style* reference only. Anything it describes —
example brands, products, people — is not a fact about the user or the current
topic. Use it for look and feel; never treat its example content as truth about
the work at hand.
