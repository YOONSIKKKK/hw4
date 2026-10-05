# Campus Customs — Design Notes

**Direction: "Swiss Collegiate."** Benchmarked against On Running's design language — Swiss
functionalism, oversized display type, hairline rules, numbered sections, restrained neutrals,
product-first imagery — then rebuilt in Campus Customs' own voice and palette. Nothing is copied
from On; what's borrowed is the *system thinking*: let the grid and the type carry the brand so
the product photography stays the loudest thing on the page.

---

## What changed

### 1. Typography

| Before | After |
|---|---|
| Georgia serif headings, modest sizes | Archivo 800 display, tight tracking (−0.035em), hero at `clamp(3rem, 12vw, 9rem)` uppercase |
| One text size for most copy | Deliberate contrast: huge display / 1rem body / 0.66rem micro-labels at 0.22em tracking |

**Why it sells:** a shopper lands and reads one thing — "BIG PRIDE, STITCHED IN BLUE" — in under
a second. Strong hierarchy removes the moment of "what is this site?" that causes bounces, and
the wide-tracked micro-labels give every section a scannable entry point so people keep moving
down the page instead of leaving.

### 2. Color

Yale navy `#00356b` and gold `#b08d50` kept as the brand, but the canvas moved from cold grey to
a warm paper `#f5f4f0`, with near-black navy `#0d1a2b` as the ink.

**Why it sells:** warm neutrals make navy garments on white photo backgrounds look like products
in a shop rather than thumbnails in a database. Navy is now used *only* for brand and action —
every blue thing on screen is either the logo or something worth clicking, so the eye finds the
buy path without hunting.

### 3. Visual hierarchy and layout

- Full-bleed hero with a hairline rule separating headline from supporting copy and CTAs.
- Numbered sections (`01 In stock now`, `02 Three reasons people walk in`) with a rule under each
  header.
- Feature tiles as a single bordered block divided by 1px gaps — one object, not three cards.
- Footer strip of facts (address, size range, assistant) on 2px top rules.

**Why it sells:** numbering implies a finite, walkable page, which keeps people scrolling to the
end rather than bailing at the first fold. The hierarchy puts "shop the collection" within the
first screen on every viewport.

### 4. How products are shown

- **Home:** a snap-scrolling horizontal rail of in-stock items, pulled live from the API.
- **Grid:** 4:5 portrait cards, image on a soft grey field, name and price on one baseline row,
  description beneath.
- **Hover:** card lifts 6px with a soft shadow, image scales 1.06, and the garment type slides up
  from the bottom edge of the photo.
- **Detail:** large image left, **sticky** info column right; colors as named dots; sizes as
  rounded chips showing the live count, sold-out ones struck through.

**Why it sells:** the rail shows stock exists before anyone clicks "Shop", which is the single
biggest reassurance on a small storefront. Price sitting on the same line as the name removes a
scan step. The sticky info column means the size chips and price never scroll away while the
shopper studies the photo — the decision stays on screen with the thing being decided about. And
a struck-through "XS Out" beside "S 25 left" is honest *and* creates urgency without a fake
countdown.

### 5. Motion

- Scroll reveal: 24px rise + fade, 0.7s, staggered 50ms per sibling.
- Nav compacts on scroll; brand mark tilts on hover.
- Buttons are pills with an ink wash that sweeps up from the bottom on hover, plus an arrow that
  nudges right.
- Ticker strip of shop facts scrolling continuously under the hero.
- Chat: panel rises and scales in, typing indicator of three blinking dots, product cards slide
  3px on hover, launcher has a slow pulsing gold dot.

**Why it sells:** motion here is all feedback, never decoration-for-its-own-sake — every hover
state answers "is this clickable?" before the shopper has to guess. The ticker gives the page a
pulse so a quiet storefront doesn't read as abandoned, and the pulsing launcher dot is what makes
people discover the assistant at all.

**Built to fail safe:** reveal animations are opt-*out*, not opt-in — elements are visible by
default and only hidden once JavaScript confirms they're below the fold. A dead timer, a stalled
observer, or `prefers-reduced-motion` can never leave a product card invisible. Reduced motion
disables all of it.

### 6. Chat interface

Rounded 18px panel with a soft deep shadow, dark header with a two-line title, messages as
asymmetric bubbles (assistant white on paper, shopper navy), results as compact tiles with
thumbnail, name, price and a short description, and a circular send button.

**Why it sells:** the panel reads like a person, not a form — which is what gets the first message
typed. Results as *tiles* rather than a paragraph of text turn a conversation directly into a
click: ask "what hoodies do you have", get eight tappable products, land on a product page. That
is the shortest path from question to purchase on the whole site, and it's one tap long.

---

## The conversion argument in one line

Big type and warm neutrals buy attention in the first second; numbered sections and a live
product rail keep people scrolling; honest per-size stock and a sticky buy column remove doubt at
the decision point; and a chat that answers with clickable product tiles collapses "I'm looking
for something" into one tap on the thing itself.
