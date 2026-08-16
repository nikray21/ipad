# Animation — the motion playbook

Motion is how you show relationships and change over time. Good motion is
mostly invisible: it makes an interface feel physical and a story feel authored.
Bad motion draws attention to itself. This is the difference between "it has
animations" and "it feels alive."

## Principles

1. **Motion has a reason.** Entrance (where did this come from), transition
   (what changed), emphasis (look here), feedback (I heard you). If you can't
   name the reason, cut it.
2. **Ease like the physical world.** Nothing in reality moves linearly.
   UI elements start fast and settle (ease-out) on entrance; ease-in on exit.
   Use spring physics for anything the user directly manipulates.
3. **Fast in, considered out.** Entrances 150–300ms. Exits can be quicker.
   Large storytelling moments (hero reveals, scroll scenes) can run 600ms–1.2s.
   Never make the user wait on repeated UI motion.
4. **Stagger to show grouping.** Reveal lists/grids with a 30–80ms per-item
   delay so the eye reads them as a set arriving, not a flash.
5. **Animate cheap properties.** `transform` and `opacity` only, for anything
   that runs every frame. Never animate `width`, `top`, `box-shadow`,
   `background` in hot paths — they trigger layout/paint and jank.
6. **One motion vocabulary.** Decide the piece's signature move (rise+fade?
   scale-from-95%? clip-reveal?) and reuse it. Randomly different transitions
   everywhere = chaos.
7. **Respect `prefers-reduced-motion`.** Always. Provide an instant/near-instant
   fallback.

## Easing curves that look designed

Never ship `ease` or `linear` for UI. Use these `cubic-bezier`s:

```css
:root {
  --ease-out-quart:  cubic-bezier(0.25, 1, 0.5, 1);      /* default UI entrance */
  --ease-out-expo:   cubic-bezier(0.16, 1, 0.3, 1);      /* dramatic settle */
  --ease-in-out-quart: cubic-bezier(0.76, 0, 0.24, 1);   /* balanced transition */
  --ease-in-back:    cubic-bezier(0.36, 0, 0.66, -0.56); /* anticipation on exit */
  --ease-out-back:   cubic-bezier(0.34, 1.56, 0.64, 1);  /* playful overshoot */
  --ease-spring:     linear(0,0.006,0.025,0.101,0.208,0.362,0.55,0.7,0.84,0.93,0.98,1,1.01,1.006,1); /* CSS spring */
}
```

The `linear()` easing function lets CSS approximate a spring without JS — great
for playful entrances. Generate custom ones at easing-generators or by sampling
a spring.

## Reduced-motion guard (put this in every animated piece)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Pattern: staggered entrance (CSS only, IntersectionObserver trigger)

```html
<div class="reveal-group">
  <div class="reveal">One</div>
  <div class="reveal">Two</div>
  <div class="reveal">Three</div>
</div>
```
```css
.reveal {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity .6s var(--ease-out-quart),
              transform .6s var(--ease-out-quart);
}
.reveal.in { opacity: 1; transform: none; }
.reveal-group.in .reveal:nth-child(1) { transition-delay: 0ms; }
.reveal-group.in .reveal:nth-child(2) { transition-delay: 60ms; }
.reveal-group.in .reveal:nth-child(3) { transition-delay: 120ms; }
```
```js
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }
}, { threshold: 0.2 });
document.querySelectorAll('.reveal, .reveal-group').forEach(el => io.observe(el));
```

For arbitrary item counts, set delay via a CSS variable:
`el.style.setProperty('--i', index)` and `transition-delay: calc(var(--i) * 60ms)`.

## Pattern: text reveal by line/word

Split into spans, mask with `overflow:hidden` wrappers, translate up. This is
the signature editorial entrance.

```js
function splitLines(el) {
  const words = el.textContent.trim().split(/\s+/);
  el.innerHTML = words.map(w =>
    `<span class="w"><span class="w-in">${w}</span></span>`).join(' ');
}
```
```css
.w { display: inline-block; overflow: hidden; vertical-align: top; }
.w-in { display: inline-block; transform: translateY(110%);
        transition: transform .8s var(--ease-out-expo); }
.in .w-in { transform: none; }
/* stagger via nth-child or JS-set delay per .w */
```

## Pattern: scroll-driven animation (native, no library)

Modern CSS scroll-driven animations — zero JS, buttery:

```css
@keyframes fade-rise { from { opacity:0; transform: translateY(40px);} to {opacity:1; transform:none;} }
.on-scroll {
  animation: fade-rise linear both;
  animation-timeline: view();          /* ties progress to element in viewport */
  animation-range: entry 0% cover 35%; /* start entering, finish 35% in */
}
```

Progress bar tied to page scroll:
```css
.progress { animation: grow linear; animation-timeline: scroll(root); transform-origin: left; }
@keyframes grow { from { transform: scaleX(0);} to { transform: scaleX(1);} }
```

For complex pinned scroll scenes (pin an element, sequence several beats as the
user scrolls), GSAP ScrollTrigger is still the most robust. Native
`animation-timeline` covers ~80% of cases with no dependency — prefer it.

## Pattern: FLIP (animate layout changes smoothly)

When something moves because layout changed (reorder, expand, filter), you
can't transition layout properties cheaply. FLIP = First, Last, Invert, Play:

```js
function flip(el, mutate) {
  const first = el.getBoundingClientRect();
  mutate();                                   // change the DOM/layout
  const last = el.getBoundingClientRect();
  const dx = first.left - last.left, dy = first.top - last.top;
  const sx = first.width / last.width, sy = first.height / last.height;
  el.animate(
    [{ transform: `translate(${dx}px,${dy}px) scale(${sx},${sy})` }, { transform: 'none' }],
    { duration: 400, easing: 'cubic-bezier(0.25,1,0.5,1)' }
  );
}
```

Modern shortcut: the **View Transitions API** does FLIP for you across DOM
changes. Wrap the mutation: `document.startViewTransition(() => updateDOM())`.
Give matching elements a shared `view-transition-name` to morph between states.

## Pattern: spring / inertia with WAAPI

For direct-manipulation feedback (buttons, cards), a short spring overshoot
feels tactile:

```js
el.animate(
  [{ transform: 'scale(1)' }, { transform: 'scale(1.06)' }, { transform: 'scale(1)' }],
  { duration: 380, easing: 'var(--ease-spring)' } // or the cubic-bezier back
);
```

## Continuous / timeline animation (motion pieces & explainers)

For an authored motion piece (not UI feedback), drive everything from ONE clock
so elements persist and interpolate across scene boundaries instead of
restarting. Structure:

```js
let t0 = performance.now();
function frame(now) {
  const t = (now - t0) / 1000; // seconds
  // derive every element's state from t via easing on scene time ranges
  setState(el, easeOutExpo(clamp01((t - 1.2) / 0.8))); // e.g. cue at 1.2s, 0.8s long
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
```

Keep a declarative scene/cue table (start, duration, easing, target) and
interpolate — this is what makes motion feel composed rather than a pile of
independent CSS animations. Prefer `transform`/`opacity`; batch DOM writes.
`canvas`/WebGL when you have hundreds of moving elements.

## Micro-interaction checklist

- Buttons: subtle scale/brightness on `:active`, not just `:hover`.
- Links: animated underline (scale/clip a pseudo-element, don't toggle
  `text-decoration`).
- Cards: lift on hover via `transform: translateY(-4px)` + shadow, ~200ms.
- Inputs: focus ring transitions in; label floats with `ease-out`.
- Loading: skeletons over spinners; shimmer via a moving gradient mask.
- Toggles/tabs: slide the active indicator (FLIP or a translated pill) so it
  travels rather than teleports.

## Performance rules

- `transform`/`opacity` only in per-frame animation.
- `will-change: transform` sparingly, on elements about to animate; remove after.
- Debounce scroll/resize; prefer `IntersectionObserver` and
  `animation-timeline` over scroll listeners.
- Test at 6x CPU throttle. If it janks, you're animating a layout property.
- Never animate more than a few dozen DOM elements at once — switch to canvas.
