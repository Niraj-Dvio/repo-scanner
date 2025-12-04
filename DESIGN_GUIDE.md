# 🎨 Visual Design Guide - RepoGuard Scanner

## Before & After Comparison

### Old UI vs New UI

#### Search Bar

**Before:**

```
Simple input field
[________username________] [🔍 Fetch Repos]
```

**After:**

```
Enhanced search with filters
┌─────────────────────────────────────────┐
│ [__________username__________] [🔍 Search] │
│ Sort by: [Updated ▼]  ☑ Include forks   │
└─────────────────────────────────────────┘
```

#### Repository Cards

**Before:**

```
┌─ Repository Name ───────── [🚀 Scan] ─┐
│ Description...                         │
│ Language: Python  ⭐ 42  📦 Forks: 5  │
└────────────────────────────────────────┘
```

**After:**

```
┌─────────────────────────────────────┐
│ ✨ Repository Name               │
│ 🟢 Scanning (beautiful status bar) │
│ Short description...               │
│ ┌──────┬──────┬──────┐            │
│ │Python│⭐150 │5.2MB │            │
│ └──────┴──────┴──────┘            │
│ 🔗 View on GitHub                  │
│ [🚀 Scan] [📊 Results]            │
└─────────────────────────────────────┘
```

#### Results Modal

**Before:**

```
Basic text display
📊 Repo Size: 100 KB
❌ Secrets Found: 3
  - secret1
  - secret2
  - secret3
✅ Dependencies: OK
```

**After:**

```
┌────────────────────────────────────────────┐
│ ✅ Scan Results                    [✕]     │
├────────────────────────────────────────────┤
│ [Overview] [🔐 Secrets (3)] [📦 Deps] [🔍 Code] │
├────────────────────────────────────────────┤
│                                            │
│ Repository Statistics                     │
│ ┌──────────┬──────────┬──────────┐       │
│ │Total: 15│ Duration:│ Files:   │       │
│ │ Issues  │ 45.2s    │ 1,250    │       │
│ └──────────┴──────────┴──────────┘       │
│                                            │
│ [📋 Copy JSON] [⬇️ Download]              │
│ [🗑️ Delete Results]                      │
└────────────────────────────────────────────┘
```

## Color Palette

### Dark Theme

```
Background:     #0f172a (Slate-900)
Surface:        #1e293b (Slate-800)
Border:         rgba(255,255,255,0.1)
Text Primary:   #ffffff
Text Secondary: #d1d5db (Gray-300)
Text Muted:     #9ca3af (Gray-400)
```

### Accent Colors

```
Primary:   #3B82F6 (Blue-500)
Secondary: #9333EA (Purple-600)
Success:   #10B981 (Green-500)
Warning:   #F59E0B (Amber-500)
Error:     #EF4444 (Red-500)
Accent:    #EC4899 (Pink-500)
```

### Status Indicators

```
Queued:     🟡 Yellow
Scanning:   🔵 Blue with spinner
Completed:  🟢 Green
Failed:     🔴 Red
```

## Typography

### Font Stack

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto",
  "Helvetica Neue", sans-serif;
```

### Font Sizes & Weights

```
H1: 2.25rem (36px) - Bold/Extrabold
H2: 1.875rem (30px) - Bold
H3: 1.5rem (24px) - Bold
Paragraph: 1rem (16px) - Regular
Small: 0.875rem (14px) - Regular
Tiny: 0.75rem (12px) - Regular
```

## Component Styling

### Button Styles

**Primary Button (Scan)**

```
Background: Linear gradient blue → purple
Hover: Enhanced shadow + scale
Active: Scale down slightly
Disabled: Gray with opacity
Animation: Smooth 200ms transition
```

**Secondary Button (Results)**

```
Background: Transparent with border
Hover: Slightly opaque background
Active: Scale down
```

**Danger Button (Delete)**

```
Background: Red with opacity
Hover: More opaque
Active: Scale effect
```

### Input Styles

```
Background: rgba(255,255,255,0.05)
Border: rgba(255,255,255,0.1)
Focus:
  - Blue border
  - Ring effect
  - Light up background
```

### Card Styles

```
Background: rgba(255,255,255,0.05) with blur
Border: rgba(255,255,255,0.1)
Hover:
  - Shadow glow
  - Border highlight
  - Scale slightly up
```

## Animations

### Entrance Animations

```
fadeIn:     0.5s ease-out
slideDown:  0.3s ease-out
slideUp:    0.3s ease-out
```

### Continuous Animations

```
blob:            7s infinite
spin:            1s linear infinite
pulse:           2s cubic-bezier ease-in-out
```

### Interactive Animations

```
Button hover:    200ms smooth transition
Loading spinner: Continuous rotation
Status update:   Quick fade transition
Modal appear:    Slide up + fade
```

## Responsive Design

### Mobile (< 640px)

```
Grid: 1 column
Padding: 1rem
Font: Slightly smaller
Spacing: Compact
```

### Tablet (640px - 1024px)

```
Grid: 2 columns
Padding: 1.5rem
Font: Normal
Spacing: Normal
```

### Desktop (> 1024px)

```
Grid: 3 columns
Padding: 2rem
Font: Normal
Spacing: Generous
```

## Spacing System

### Margin/Padding Scale

```
xs: 0.25rem (4px)
sm: 0.5rem (8px)
md: 1rem (16px)
lg: 1.5rem (24px)
xl: 2rem (32px)
2xl: 3rem (48px)
```

## Border Radius

```
Small:   0.375rem (6px)   - Small elements
Normal:  0.5rem (8px)     - Inputs, buttons
Large:   0.75rem (12px)   - Cards
XL:      1rem (16px)      - Large modals
Full:    9999px           - Pills, circles
```

## Shadow System

### Shadow Levels

```
Small:   0 1px 2px rgba(0,0,0,0.05)
Medium:  0 4px 6px rgba(0,0,0,0.1)
Large:   0 10px 15px rgba(0,0,0,0.2)
XL:      0 20px 25px rgba(0,0,0,0.3)
Glow:    0 0 30px rgba(59,130,246,0.3)
```

## Accessibility Features

### Color Contrast

- ✅ All text meets WCAG AA standards
- ✅ Status indicators not color-only (have icons)
- ✅ Focus states clearly visible

### Keyboard Navigation

- ✅ Tab through all interactive elements
- ✅ Enter key activates buttons
- ✅ Escape closes modals
- ✅ Logical tab order

### Screen Reader Support

- ✅ Semantic HTML structure
- ✅ ARIA labels on interactive elements
- ✅ Alt text on images (none in this design)
- ✅ Form labels associated with inputs

## Micro-Interactions

### Button Feedback

```
Hover:   Glow effect + scale (1.02x)
Active:  Scale down (0.98x)
Focus:   Ring effect
Disabled: Opacity 50%
```

### Input Feedback

```
Focus:   Border color + ring
Error:   Red border + icon
Success: Green indicator
```

### Status Changes

```
Queued → Scanning:   Smooth transition
Scanning → Complete: Success animation
Complete → Failed:   Error animation
```

## Layout Patterns

### Search Section

```
Max-width: Full
Padding: 2rem
Background: Glassmorphic card
Border: Subtle border
```

### Grid System

```
Gap: 1.5rem (24px)
Columns: 1 | 2 | 3 (responsive)
Auto-flow: Dense
```

### Modal

```
Max-width: 56rem (896px)
Overlay: Dark semi-transparent
Animation: Slide up + fade
Position: Centered, fixed
```

## Theme Consistency

### Color Usage Rules

1. Primary color for main actions
2. Secondary for alternates
3. Success for positive states
4. Warning for caution
5. Error for problems
6. Neutral for secondary info

### Typography Rules

1. Single font family throughout
2. Maximum 3 font weights (Regular, Semibold, Bold)
3. Consistent line heights (1.5, 1.6)
4. Proper hierarchy with size/weight

### Spacing Rules

1. Use scale multiples (8px base)
2. Consistent padding in cards
3. Even margins between sections
4. Breathing room around content

## Dark Mode Specific

### Background Gradient

```
from:  #0f172a (Slate-900)
via:   #1e293b (Slate-800)
to:    #0f172a (Slate-900)
```

### Overlay Effects

- Multiple layers of rgba effects
- Blur backdrop filters
- Subtle glow effects

### Text Contrast

- Primary text: Near white (#ffffff)
- Secondary text: Light gray (#d1d5db)
- Muted text: Medium gray (#9ca3af)

## Glassmorphism Details

### Glass Card Formula

```css
backdrop-filter: blur(10px);
background: rgba(255, 255, 255, 0.05);
border: 1px solid rgba(255, 255, 255, 0.1);
```

### Glowing Borders (on hover)

```css
box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
border-color: rgba(59, 130, 246, 0.5);
```

## Performance Notes

### GPU Acceleration

- CSS transforms for animations
- Will-change hints on animations
- Backdrop filter for glass effect

### Animation Performance

- Prefers-reduced-motion supported
- Reasonable animation durations
- No blocking animations

---

**Design System Version**: 2.0
**Last Updated**: December 2025
**Status**: Production Ready
