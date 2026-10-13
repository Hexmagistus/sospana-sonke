# ADR 0001: Dimensional surfaces and a gated hero globe

Date: 2026-10-13

## Context

The shared navy and teal chrome is flat: one shadow on a card, a flat teal button, and a text hero. The owner asked for the site to feel three-dimensional and realistic, including a hero globe, without giving up the mobile performance and accessibility bars already met on the live homepage and role lists.

## Decision

Depth is painted with CSS on the shared card and the teal button: a top highlight, a soft stacked shadow, and a pressed-in shadow on activation. A single pointer listener tilts a card a few degrees while a fine pointer is over it. That listener ignores touch, so a finger scroll does not tilt the card under it. Cards that already tilt themselves, sticky search forms, and form controls are left still.

The hero always includes a painted globe in the HTML. On a wide screen with a fine pointer, no data-saver, no slow connection, at least four cores, and no reduced-motion setting, the page may load a WebGL globe after the browser is idle. That module is a separate chunk (`three` and `@react-three/fiber`) and is not requested otherwise. The canvas sits in the same fixed box as the painting, so the swap does not move the headline.

The labour page keeps its 2D table. The summary bars stay flat. Their length is the printed rate. A recessed track and a highlight on the fill are shading only. There is no perspective and no extruded bar.

## Consequences

Phones, slow connections, data-saver, and reduced motion see the painted globe and the still surfaces. They do not download the WebGL chunk. Reduced motion also cancels tilt and the button's press movement. Keyboard focus rings stay. The globe is decorative and is hidden from assistive technology. The headline, the search, and the labour numbers remain the content.

## Limits

Mobile Lighthouse performance stays at 90 or above, accessibility at 100, and cumulative layout shift under 0.1. Contrast for text is unchanged. Nothing in this treatment covers or delays the headline.
