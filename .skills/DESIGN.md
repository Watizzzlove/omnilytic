---
version: alpha
name: Omnilytic-design-system
description: |
  A confident monochrome dashboard frame interrupted by oversized pastel color-block sections. The chrome — top nav, body type, tabs, footer — is rigorously black and white, while each major section drops into a saturated lime, lavender, cream, mint, or pink panel that reads like a sticky note placed on a clean desk. Every CTA is a pill, every card is a hairline-bordered rectangle, and the result is a data tool that feels both technical and joyful.

colors:
  ink: "#000000"
  canvas: "#ffffff"
  inverse-canvas: "#000000"
  inverse-ink: "#ffffff"
  on-inverse-soft: "#ffffff"
  hairline: "#e6e6e6"
  hairline-soft: "#f1f1f1"
  surface-soft: "#f7f7f5"
  block-lime: "#dceeb1"
  block-lilac: "#c5b0f4"
  block-cream: "#f4ecd6"
  block-pink: "#efd4d4"
  block-mint: "#c8e6cd"
  block-coral: "#f3c9b6"
  block-navy: "#1f1d3d"
  accent-magenta: "#ff3d8b"
  semantic-success: "#1ea64a"
  semantic-danger: "#d8373a"
  semantic-warning: "#d98c10"

typography:
  display-lg:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 32px
    fontWeight: 340
    lineHeight: 1.10
    letterSpacing: -0.48px
  headline:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 22px
    fontWeight: 540
    lineHeight: 1.35
    letterSpacing: -0.22px
  subhead:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 22px
    fontWeight: 340
    lineHeight: 1.35
    letterSpacing: -0.22px
  card-title:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 20px
    fontWeight: 700
    lineHeight: 1.45
  body-lg:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 18px
    fontWeight: 330
    lineHeight: 1.40
  body:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 16px
    fontWeight: 320
    lineHeight: 1.45
  body-sm:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 14px
    fontWeight: 330
    lineHeight: 1.45
  button:
    fontFamily: Inter, system-ui, helvetica
    fontSize: 16px
    fontWeight: 480
    lineHeight: 1.40
  eyebrow:
    fontFamily: "JetBrains Mono", "SF Mono", monospace
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.30
    letterSpacing: 0.42px
  caption:
    fontFamily: "JetBrains Mono", "SF Mono", monospace
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.00
    letterSpacing: 0.48px

rounded:
  sm: 6px
  md: 8px
  lg: 24px
  pill: 50px
  full: 9999px

spacing:
  hair: 1px
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 80px

components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 8px 20px
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    border: 1px solid "{colors.ink}"
    padding: 7px 19px
  button-tab:
    backgroundColor: "transparent"
    textColor: "{colors.hairline}"
    typography: "{typography.button}"
    rounded: "{rounded.none}"
    padding: 8px 16px
  button-tab-active:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.none}"
  top-nav:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    height: 56px
  kpi-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: 16px
  kpi-value:
    typography: "{typography.display-lg}"
    textColor: "{colors.ink}"
  section-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: 20px
    border: 1px solid "{colors.hairline}"
  color-block-section:
    backgroundColor: "{colors.block-lime}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 32px
  color-block-section-lilac:
    backgroundColor: "{colors.block-lilac}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 32px
  color-block-section-navy:
    backgroundColor: "{colors.block-navy}"
    textColor: "{colors.inverse-ink}"
    rounded: "{rounded.lg}"
    padding: 32px
  funnel-bar:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.pill}"
    padding: 8px 16px
  badge:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 10px
  badge-success:
    backgroundColor: "#e6f7e6"
    textColor: "{colors.semantic-success}"
    rounded: "{rounded.pill}"
  badge-danger:
    backgroundColor: "#fce8e8"
    textColor: "{colors.semantic-danger}"
    rounded: "{rounded.pill}"
  text-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: 10px 14px
    border: 1px solid "{colors.hairline}"
  text-input-focused:
    borderColor: "{colors.ink}"
---

## Overview

Omnilytic's design system is adapted from Figma's marketing language: a monochrome chrome (black ink on white canvas) with oversized pastel **color-block sections** that define the narrative rhythm. The chrome — top nav, body text, tabs, CTAs — stays in black and white. Each dashboard section (Command Center, Matrix, Actions) drops into a full-width pastel panel with rounded corners, making data sections feel like intentional storytelling surfaces rather than generic cards.

The system substitutes **Inter** for figmaSans (same fine-grained weight axis) and **JetBrains Mono** for figmaMono (eyebrows and captions only). All CTAs are pills, all cards are hairline-bordered rectangles with `{rounded.sm}` corners, and no shadows exist — the color blocks are the depth device.

### Key Characteristics
- Monochrome system core: `{colors.ink}` (black) and `{colors.canvas}` (white) carry every CTA, every nav link, every body line.
- Oversized pastel color-block sections (`{colors.block-lime}`, `{colors.block-lilac}`, `{colors.block-cream}`, `{colors.block-mint}`, `{colors.block-pink}`, `{colors.block-navy}`) define each major dashboard section.
- All CTAs are pills (`{rounded.pill}`). No square buttons.
- Inter variable typeface at fine weight increments (320, 330, 340, 480, 540, 700).
- JetBrains Mono reserved for KPI values, captions, and data labels — always with positive letter-spacing.
- No drop shadows on color blocks or cards — hairline borders (`{colors.hairline}` 1px) carry the container language.

## Colors

### Brand
- **Ink** (`{colors.ink}` — `#000000`): all body text, headlines, primary CTA fill, nav links. True black.
- **Canvas** (`{colors.canvas}` — `#ffffff`): page background, card surfaces, secondary CTA background.
- **Surface Soft** (`{colors.surface-soft}` — `#f7f7f5`): off-white tile backgrounds for dropdown menus, secondary containers.

### Color Block Palette
- **Lime** (`{colors.block-lime}` — `#dceeb1`): Command Center section
- **Lilac** (`{colors.block-lilac}` — `#c5b0f4`): Matrix section
- **Cream** (`{colors.block-cream}` — `#f4ecd6`): Actions section
- **Navy** (`{colors.block-navy}` — `#1f1d3d`): AI Analysis section (inverse)

### Semantic
- **Success** (`{colors.semantic-success}` — `#1ea64a`): positive dynamics, badges
- **Danger** (`{colors.semantic-danger}` — `#d8373a`): negative dynamics, problems
- **Warning** (`{colors.semantic-warning}` — `#d98c10`): attention-needed items
- **Accent Magenta** (`{colors.accent-magenta}` — `#ff3d8b`): promotional CTAs

### Borders
- **Hairline** (`{colors.hairline}` — `#e6e6e6`): default card and input borders
- **Hairline Soft** (`{colors.hairline-soft}` — `#f1f1f1`): subtle row dividers

## Typography

### Font Family
- **Inter** — variable sans; fallback `system-ui, helvetica`. Used for all body, headline, and button text. Weight axis exercised at fine increments: 320, 330, 340, 480, 540, 700.
- **JetBrains Mono** — monospace; fallback `SF Mono, monospace`. Reserved for KPI values, data labels, eyebrows, and captions. Always uppercase with positive letter-spacing when used as labels.

### Hierarchy
| Token | Size | Weight | Line Height | Use |
|---|---|---|---|---|
| `{typography.display-lg}` | 32px | 340 | 1.10 | KPI values, hero numbers |
| `{typography.headline}` | 22px | 540 | 1.35 | Section titles, block headers |
| `{typography.subhead}` | 22px | 340 | 1.35 | Intro text at headline scale |
| `{typography.card-title}` | 20px | 700 | 1.45 | Card titles, action headers |
| `{typography.body-lg}` | 18px | 330 | 1.40 | Lead body, form labels |
| `{typography.body}` | 16px | 320 | 1.45 | Default body text |
| `{typography.body-sm}` | 14px | 330 | 1.45 | Card details, table cells |
| `{typography.button}` | 16px | 480 | 1.40 | All pill buttons |
| `{typography.eyebrow}` | 14px | 400 | 1.30 | Section labels (JetBrains Mono, uppercase) |
| `{typography.caption}` | 12px | 400 | 1.00 | Captions, badges (JetBrains Mono, uppercase) |

## Shapes

| Token | Value | Use |
|---|---|---|
| `{rounded.sm}` | 6px | Cards, inputs, section containers |
| `{rounded.md}` | 8px | Larger containers, image frames |
| `{rounded.lg}` | 24px | Color-block sections |
| `{rounded.pill}` | 50px | All CTAs |
| `{rounded.full}` | 9999px | Icon buttons, status dots |

## Components

### Buttons
- **`button-primary`** — black pill with white text. Every primary CTA in the system.
- **`button-secondary`** — white pill with black text and 1px ink border. Paired with primary for secondary actions.
- **`button-tab`** / **`button-tab-active`** — text-only tab with 2px bottom border on active state. Used in navigation tabs.

### Navigation
- **`top-nav`** — white bar, 56px height, hairline bottom border. Brand mark at left, action buttons at right.

### Cards
- **`kpi-card`** — hairline-bordered rectangle, 6px radius, 16px padding. Holds single KPI metric.
- **`section-card`** — hairline-bordered section container for tables, lists, and detail content.
- **`funnel-bar`** — black pill bar showing funnel stage width proportionally.

### Color-Block Sections
- **`color-block-section`** — lime ground for Command Center overview content.
- **`color-block-section-lilac`** — lilac ground for Matrix section.
- **`color-block-section-navy`** — deep navy ground for AI Analysis panel (inverse text).

### Badges
- **`badge`** — soft-gray pill for neutral labels.
- **`badge-success`** / **`badge-danger`** — semantic colored pills for dynamics and status indicators.

## Do's and Don'ts

### Do
- Use `{rounded.pill}` for every CTA button.
- Use `{rounded.sm}` for every card and input container.
- Keep CTAs in `{colors.ink}` / `{colors.canvas}` only — reserved magenta for promotional use.
- Allow white canvas to separate color-block sections — never stack two pastel blocks directly.
- Use JetBrains Mono only for data values, captions, and labels — never for body paragraphs.
- Let color blocks substitute for elevation — no shadows.

### Don't
- Don't use mid-gray text. Hierarchy comes from weight, not opacity.
- Don't add shadows to cards or color blocks.
- Don't introduce new accent colors outside the documented block palette.
- Don't square off CTAs.
- Don't stack multiple color blocks without white canvas between them.

## Responsive Behavior

| Width | Changes |
|---|---|
| < 1024px | KPI grid collapses 4→2 columns |
| < 810px | Body padding tightens, nav stacks vertically, tabs go full-width, grids become single column |
| < 560px | Color blocks go full-bleed (remove side padding) |
