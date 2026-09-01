# HTML email — design inside the hardest constraints

Email clients (especially Outlook) are a decade behind browsers. Email is its
own discipline: table layouts, inline styles, and defensive coding. Beautiful is
possible, but only within the rules.

## Golden rules

- **Tables for layout.** `<table role="presentation">` nested as needed. No
  flexbox/grid for structure (unsupported in Outlook/older clients).
- **Inline every style** with `style=""`. `<style>` in `<head>` is stripped or
  ignored by many clients (keep it only for progressive enhancement + media
  queries). Tools/build steps can inline for you; if hand-writing, inline.
- **Single file, ~600px content width.** 600px is the safe email column width.
- **Images are decoration, not content.** Many clients block images by default
  — critical text must be real text, not baked into an image. Always set `alt`.
- **Web-safe fonts** with graceful fallback: Arial/Helvetica, Georgia,
  Times, Verdana, Tahoma. Custom web fonts work in *some* clients — always stack
  a web-safe fallback; never depend on the custom font.

## Skeleton

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:#f4f4f4;margin:0;padding:0">
  <tr><td align="center" style="padding:24px">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
      style="width:600px;max-width:600px;background:#ffffff">
      <tr><td style="padding:32px;font-family:Arial,Helvetica,sans-serif;
        font-size:16px;line-height:1.5;color:#1a1a1a">
        <!-- content -->
      </td></tr>
    </table>
  </td></tr>
</table>
```

## Buttons (bulletproof)

Padded-anchor style works nearly everywhere; VML for Outlook if you must:
```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
  <td align="center" bgcolor="#1a1a1a" style="border-radius:4px">
    <a href="#" style="display:inline-block;padding:14px 28px;font-family:Arial,sans-serif;
      font-size:16px;color:#ffffff;text-decoration:none;font-weight:bold">Read more</a>
  </td></tr></table>
```

## Responsive (progressive enhancement)

Media queries work in many modern clients; design mobile-safe first (single
column, ≥16px text, ≥44px tap targets) so it's fine even where media queries are
ignored:
```html
<style>
  @media (max-width:600px){
    .col{width:100%!important;display:block!important}
    .pad{padding:20px!important}
  }
</style>
```

## Dos & don'ts

- Do: set explicit `width`/`height` on images; use `border="0"`; give a plain
  bg color fallback behind any background image; keep total weight low; test in
  real clients (Litmus/Email on Acid).
- Don't: rely on background images (Outlook), `position`, `float` for structure,
  external CSS, JS (stripped), forms (mostly stripped), video (fallback to a
  linked image), custom fonts without fallback.
- Always include a plain-text alternative and a visible unsubscribe/footer for
  real sends.

## Design within the box

Constraints don't mean ugly: strong type hierarchy, generous padding, one
accent, a clear single CTA, real content, and a consistent 600px rhythm produce
a clean, premium email. Restraint reads as quality here more than anywhere.
