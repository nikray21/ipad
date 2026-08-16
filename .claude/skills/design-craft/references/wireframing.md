# Wireframing & ideation — explore before you commit

The biggest quality gains happen before pixels. Wireframing is how you try ten
structures cheaply instead of polishing the first mediocre one. Do this when the
structure or flow is uncertain — skip it when the layout is obvious.

## Purpose

- Decide **content, hierarchy, and flow** without the distraction of color/type/
  polish.
- Explore **many** arrangements fast — quantity first, then pick and refine.
- Align with the user on structure before investing in craft.

## Low-fi rules

- Grayscale only. Boxes, lines, and real-ish placeholder labels (not lorem —
  write the actual kind of content: "Headline: the one promise", "Primary CTA").
- Real hierarchy even in gray: size and weight still communicate importance.
- Show the states and the flow, not just one happy screen: the empty state, the
  filled state, the error, the next screen.
- Don't style. If you're picking a font in a wireframe, you've skipped ahead.

## Explore breadth (storyboard the options)

For any non-trivial screen, sketch 3–6 structurally different takes:
- Nav as top bar vs. sidebar vs. bottom tabs.
- Content as feed vs. grid vs. focused single-column.
- Hero-led vs. straight-to-content.
- Wizard/steps vs. single long form.

Lay them side by side. Structurally different — not five tweaks of one idea.
Name the tradeoff each makes (density vs. focus, discovery vs. speed).

## Storyboards (flows)

For a flow, draw the sequence of frames left-to-right: entry → each step →
success, plus the branch (error/empty). This surfaces missing states and
awkward transitions before you build them. Annotate what triggers each
transition and what animates.

## Simple wireframe kit (plain HTML)

```css
.wire{--ink:#111;--mut:#999;--line:#ddd;font-family:ui-sans-serif,sans-serif;color:var(--ink)}
.wire .box{border:1.5px solid var(--line);border-radius:6px;background:#fafafa}
.wire .ph{background:repeating-linear-gradient(45deg,#eee,#eee 6px,#f6f6f6 6px,#f6f6f6 12px)}
.wire .txt{height:10px;border-radius:3px;background:var(--line)}
.wire .txt.short{width:40%} .wire .txt.mid{width:70%}
.wire .btn{display:inline-block;padding:10px 18px;border:1.5px solid var(--ink);border-radius:6px;font-weight:600}
.wire .label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
```
Compose screens from these primitives; annotate with the `.label` class.

## From wireframe to hi-fi

Once structure is agreed: pick the direction (aesthetics.md), build the system
(workflow.md), then apply. The wireframe becomes the skeleton; craft is the
flesh. Don't let a wireframe's gray boxes survive into the final — they're
scaffolding.

## When to skip

- Tiny changes, obvious layouts, or when the user gave you a clear reference/
  structure already. Wireframing a login form is procrastination.
