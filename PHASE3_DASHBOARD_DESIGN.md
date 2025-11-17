# Phase 3: Real-Time Market Data Dashboard - Design Document

**Project**: NQ=F Real-Time Market Data Dashboard  
**Phase**: Phase 3 - Frontend Dashboard UI  
**Status**: In Development  
**Last Updated**: 2025-11-17  

---

## Executive Summary

Phase 3 implements a production-ready, responsive real-time market data dashboard that consumes the 16 API endpoints from Phase 2. The dashboard features six major components displaying market status, pricing, reference levels, session ranges, Fibonacci pivots, and hourly block segmentation. All data refreshes automatically every 75 seconds with smooth animations and comprehensive error handling.

---

## Layout Architecture

### Wireframe: Desktop (992px+)

```
┌─────────────────────────────────────────────────────────────────┐
│ NQ=F Dashboard     | Current Time ET    | Market Status: OPEN   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Market       │  │ Current      │  │ Reference    │          │
│  │ Status       │  │ Price        │  │ Levels       │          │
│  │ Timer        │  │ Display      │  │ Table        │          │
│  │              │  │              │  │              │          │
│  │ countdown    │  │ 17245.50 up  │  │ Level | Dist │          │
│  │ hours ops    │  │ +125.25 0.73%│  │ R1    | +45  │          │
│  │              │  │ H:L          │  │ PP    | -2   │          │
│  │              │  │              │  │ S1    | -60  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Session      │  │ Fibonacci    │  │ Hourly       │          │
│  │ Ranges       │  │ Pivots       │  │ Blocks       │          │
│  │              │  │              │  │              │          │
│  │ Asian/London │  │ Weekly/Daily │  │ Progress 3/7 │          │
│  │ NY AM/PM     │  │ R3-S3        │  │ Block bars   │          │
│  │              │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Wireframe: Tablet (576px - 991px)

```
┌─────────────────────────────────────────┐
│ NQ=F Dashboard    | Time | Status: OPEN│
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐  ┌──────────────┐│
│  │ Market Status    │  │ Current      ││
│  │ Timer            │  │ Price        ││
│  │                  │  │              ││
│  └──────────────────┘  └──────────────┘│
│                                         │
│  ┌──────────────────────────────────────┐│
│  │ Reference Levels                     ││
│  │ Level | Distance                     ││
│  └──────────────────────────────────────┘│
│                                         │
│  ┌──────────────────┐  ┌──────────────┐│
│  │ Session Ranges   │  │ Fibonacci    ││
│  │                  │  │ Pivots       ││
│  └──────────────────┘  └──────────────┘│
│                                         │
│  ┌──────────────────────────────────────┐│
│  │ Hourly Blocks                        ││
│  │ Progress: 3/7                        ││
│  └──────────────────────────────────────┘│
│                                         │
└─────────────────────────────────────────┘
```

### Wireframe: Mobile (320px - 575px)

```
┌─────────────────────┐
│ NQ=F Dashboard      │
│ Time | Status: OPEN │
├─────────────────────┤
│                     │
│ ┌─────────────────┐ │
│ │ Market Status   │ │
│ │ Timer           │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Current Price   │ │
│ │ 17245.50        │ │
│ │ +125.25 0.73%   │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Reference       │ │
│ │ Levels          │ │
│ │ (scrollable)    │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Session Ranges  │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Fibonacci       │ │
│ │ Pivots          │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Hourly Blocks   │ │
│ │ 3/7 blocks      │ │
│ └─────────────────┘ │
│                     │
└─────────────────────┘
```

---

## Component Specifications

### 1. MarketStatusTimer Component

**Responsibilities:**
- Display current time in ET timezone with ISO 8601 format
- Show market status (OPEN, CLOSED, MAINTENANCE)
- Display countdown to next market event
- Show hours of operation text
- Auto-update countdown every second

**Data Source:**
- `/api/market-status/{ticker}` endpoint
- Fields: status, current_time_et, next_event (with countdown_seconds)

**States:**
- Loading: Skeleton or spinner during initial fetch
- Live: Status badge with color (green=OPEN, gray=CLOSED, yellow=MAINTENANCE)
- Error: Display last known status with error message

**Visual Design:**
- Large, prominent time display (h1 or h2)
- Color-coded status badge
- Countdown in human-readable format (e.g., "48h 30m 45s")
- Hours of operation in smaller text

---

### 2. CurrentPriceDisplay Component

**Responsibilities:**
- Display current price in large, prominent format
- Show change amount and percentage with color coding
- Display daily high and low
- Show last update timestamp
- Indicator for live/delayed data

**Data Source:**
- `/api/current-price/{ticker}` endpoint
- Fields: current_price, change, change_percent, daily_high, daily_low, last_update_time

**States:**
- Loading: Skeleton placeholder
- Live: Real data with up/down arrow indicators
- Error: Show last known price with error message

**Visual Design:**
- Price in very large font (4rem-5rem on desktop)
- Change indicator: Green for positive, red for negative
- Up/down arrows for visual clarity
- Daily range bar showing price position within high/low
- Timestamp in smaller, muted text

---

### 3. ReferenceLevelsTable Component

**Responsibilities:**
- Display all 16 reference levels in organized table
- Color-code proximity status: ABOVE (red), NEAR (yellow), BELOW (green)
- Show distance from current price
- Highlight closest level
- Organize levels logically (weekly, daily, intraday, etc.)

**Data Source:**
- `/api/reference-levels/{ticker}` endpoint
- Fields: reference_levels (16 levels), signals (proximity info), closest_level

**Reference Levels Include:**
1. Weekly Open
2. Weekly High
3. Weekly Low
4. Daily Open
5. Daily High
6. Daily Low
7. 4-hour Open
8. 4-hour High
9. 4-hour Low
10. 1-hour Open
11. 1-hour High
12. 1-hour Low
13. 15-min Open
14. 15-min High
15. 15-min Low
16. Previous Day Close

**Visual Design:**
- Table with columns: Level Name | Price | Distance | Proximity Badge
- Color-coded proximity badges:
  - Red: ABOVE (price > level + threshold)
  - Yellow: NEAR (within threshold)
  - Green: BELOW (price < level - threshold)
- Highlight closest level with stronger emphasis
- Scrollable on mobile, fixed on desktop
- Responsive table with abbreviations on mobile

---

### 4. SessionRanges Component

**Responsibilities:**
- Display 4 trading sessions: Asian, London, NY AM, NY PM
- Show high/low per session with range
- Indicate if price is within/above/below range
- Display bar count for each session
- Visual range indicator

**Data Source:**
- `/api/session-ranges/{ticker}` endpoint
- Fields: current_session_ranges, previous_day_session_ranges
- Per session: name, high, low, range, bars_in_session, within_range, above_range, below_range

**Sessions Included:**
1. Asian: 18:00-02:00 ET (Sunday night - Monday morning)
2. London: 02:00-08:00 ET (Early morning)
3. NY AM: 08:00-12:00 ET (Opening hours)
4. NY PM: 12:00-17:00 ET (Afternoon)

**Visual Design:**
- Card per session with expandable detail
- Visual range bar showing H/L with current price position
- Color-coded indicator: Green if within range, red if outside
- Bar count indicator (e.g., "42 bars")
- Time range label in smaller text
- Previous day toggle (optional)

---

### 5. FibonacciPivots Component

**Responsibilities:**
- Display weekly and daily pivot levels
- Show 7 levels per timeframe: R3, R2, R1, PP, S1, S2, S3
- Color-code resistance (R) and support (S) levels
- Show distance from current price
- Highlight closest pivot

**Data Source:**
- `/api/fibonacci-pivots/{ticker}` endpoint
- Fields: weekly_pivots, daily_pivots, closest_pivot
- Per pivot: R3, R2, R1, PP, S1, S2, S3 prices

**Visual Design:**
- Two sections: Weekly | Daily (tabs or side-by-side on desktop)
- Vertical level display with resistance (top) to support (bottom)
- Pivot point (PP) in center, highlighted
- Distance from current price shown
- Color scheme:
  - Resistance levels: Red gradient
  - Pivot point: Neutral/blue
  - Support levels: Green gradient
- Closest level highlighted with stronger emphasis

---

### 6. HourlyBlockSegmentation Component

**Responsibilities:**
- Display 7 blocks per hour (~8.57 min each)
- Show progress bar (X/7 blocks completed)
- Highlight current/active block
- Display OHLC summary for current block
- Visual completion indicator

**Data Source:**
- `/api/hourly-blocks/{ticker}` endpoint
- Fields: blocks array with: block_num, start_time, end_time, is_complete
- Current block OHLC data

**Visual Design:**
- Horizontal progress bar with 7 segments
- Current block highlighted (different color)
- Completed blocks filled, incomplete blocks empty
- Progress text: "3 of 7 blocks" or similar
- Current block OHLC in small card below bar:
  - Open | High | Low | Close | Time
- Responsive: Full bar on desktop, compressed on mobile

---

## Responsive Breakpoints

### Mobile-First Approach (320px - 575px)

**Layout:**
- Single-column layout
- Full-width components stacked vertically
- Scrollable main container
- Bottom navigation for additional controls (optional)

**Typography:**
- Body text: 16px minimum (no zoom)
- Component titles: 20px (h5)
- Data values: 24px-32px
- Status labels: 14px

**Spacing:**
- Component padding: 16px
- Component margin: 12px
- Grid gaps: 12px

**Touch Targets:**
- Minimum 44x44px for interactive elements
- Larger tap areas for filters/buttons

---

### Tablet (576px - 991px)

**Layout:**
- 2-column grid for main components
- Top row: Market Status + Current Price
- Second row: Reference Levels (full width)
- Third row: Session Ranges + Fibonacci Pivots
- Bottom row: Hourly Blocks (full width)

**Typography:**
- Body text: 15px
- Component titles: 22px (h4)
- Data values: 28px-36px

**Spacing:**
- Component padding: 18px
- Component margin: 14px
- Grid gaps: 16px

---

### Desktop (992px+)

**Layout:**
- 3-column grid for main components
- Top row: Market Status | Current Price | Reference Levels
- Bottom row: Session Ranges | Fibonacci Pivots | Hourly Blocks
- Full-width optional sections for details

**Typography:**
- Body text: 14px
- Component titles: 24px (h3)
- Data values: 32px-48px

**Spacing:**
- Component padding: 20px
- Component margin: 16px
- Grid gaps: 20px

---

## Auto-Refresh Mechanism

### Refresh Strategy

**Interval:** 75 seconds (configurable)
**Method:** Parallel API calls using Fetch API
**Timing:** Staggered requests to avoid thundering herd

**Implementation:**
```javascript
const REFRESH_INTERVAL = 75000; // 75 seconds
const ticker = 'NQ=F';

setInterval(async () => {
  try {
    // Parallel fetch all 6 endpoints
    const [
      marketStatus,
      currentPrice,
      referenceLevels,
      sessionRanges,
      fibonacciPivots,
      hourlyBlocks
    ] = await Promise.all([
      fetch(`/api/market-status/${ticker}`),
      fetch(`/api/current-price/${ticker}`),
      fetch(`/api/reference-levels/${ticker}`),
      fetch(`/api/session-ranges/${ticker}`),
      fetch(`/api/fibonacci-pivots/${ticker}`),
      fetch(`/api/hourly-blocks/${ticker}`)
    ]);

    // Update components with new data
    updateComponents(data);
    
  } catch (error) {
    handleRefreshError(error);
  }
}, REFRESH_INTERVAL);
```

### Loading States

- Show subtle loading indicator during refresh
- Fade out old data slightly while loading new
- Smooth transition with CSS animations (0.3s)
- Do NOT fully disable UI during refresh

### Error Handling

- Network errors: Show toast message, retry in 30 seconds
- API errors (4xx/5xx): Show error message, fallback to cached data
- Timeout errors (>5s): Show "data may be outdated" warning
- Retry logic: Exponential backoff (1s, 2s, 4s, 8s, 16s)

---

## Styling & Color Scheme

### Color Palette

**Primary Colors:**
- Primary Blue: #0d6efd (Bootstrap default)
- Success Green: #198754 (below/support)
- Danger Red: #dc3545 (above/resistance)
- Warning Yellow: #ffc107 (near/neutral)

**Status Indicators:**
- Market Open: Green (#198754)
- Market Closed: Gray (#6c757d)
- Maintenance: Yellow (#ffc107)

**Proximity Colors:**
- BELOW (Support): Green (#198754)
- NEAR (Neutral): Yellow (#ffc107)
- ABOVE (Resistance): Red (#dc3545)

**Text Colors:**
- Primary Text: #212529 (dark mode: #e9ecef)
- Secondary Text: #6c757d (dark mode: #adb5bd)
- Muted Text: #999 (timestamps, secondary info)

### Typography Scale

```css
h1: 48px, weight 700, color: #212529
h2: 32px, weight 700, color: #212529
h3: 24px, weight 600, color: #212529
h4: 20px, weight 600, color: #212529
h5: 18px, weight 600, color: #212529
body: 14px, weight 400, color: #6c757d
small: 12px, weight 400, color: #999
```

### Spacing System (8px base)

```
xs: 4px (0.25rem)
sm: 8px (0.5rem)
md: 12px (0.75rem)
lg: 16px (1rem)
xl: 20px (1.25rem)
2xl: 24px (1.5rem)
3xl: 32px (2rem)
```

### Border Radius

- Cards: 8px
- Buttons: 4px
- Badges: 4px
- Progress bars: 4px

### Shadows

- Card shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075)
- Hover shadow: 0 0.5rem 1rem rgba(0,0,0,0.15)
- Active shadow: inset 0 0.125rem 0.25rem rgba(0,0,0,0.075)

---

## Accessibility (WCAG 2.1 AA)

### Requirements

1. **Semantic HTML:**
   - Use proper heading hierarchy (h1-h6)
   - Use semantic tags: <table>, <section>, <article>
   - Proper label associations with form elements

2. **Color Contrast:**
   - All text has minimum 4.5:1 contrast ratio (AA)
   - 3:1 for large text (18px+ or 14px+ bold)
   - Do NOT rely on color alone for information

3. **ARIA Labels:**
   - Add aria-label to icon buttons
   - Use aria-describedby for supplemental info
   - Use aria-live="polite" for auto-updated regions
   - Proper role attributes for custom components

4. **Keyboard Navigation:**
   - All interactive elements focusable (tabindex)
   - Focus indicators visible (minimum 2px border)
   - Logical tab order (top-to-bottom, left-to-right)
   - Escape key to close modals/dropdowns

5. **Screen Reader Support:**
   - Status updates announced via aria-live
   - Charts described with text alternative
   - Abbreviations explained with <abbr> title

6. **Font Sizing:**
   - No fixed sizes (use rem, %, em)
   - Body text minimum 16px on mobile
   - Respect user zoom preferences

---

## Performance Considerations

### Optimization Strategies

1. **Bundle Size:**
   - Bootstrap 5 (~50KB gzipped)
   - Chart.js (~45KB gzipped, if needed for future charting)
   - Custom CSS: <10KB gzipped
   - Custom JS: <20KB gzipped

2. **Lazy Loading:**
   - Load reference levels table lazily on mobile
   - Defer Chart.js if used for charts
   - Preload critical API endpoints

3. **Caching:**
   - Cache API responses in localStorage
   - Use etags for conditional requests
   - Clear cache on logout or every 24 hours

4. **Rendering:**
   - Virtual scrolling for large tables (100+ rows)
   - Debounce resize event listeners
   - Use CSS containment for performance
   - Minimize layout thrashing in JS

---

## Testing Strategy

### Unit Tests (JavaScript)
- Test auto-refresh interval and cleanup
- Test data formatting functions
- Test error handling logic
- Test countdown calculation

### Integration Tests
- API endpoint integration
- Data binding and template rendering
- Error scenarios and fallbacks
- Timezone conversion accuracy

### E2E Tests
- Dashboard loads successfully
- Auto-refresh works every 75 seconds
- Responsive layout on mobile/tablet/desktop
- Error states handled gracefully
- Timezone displays correctly (ET vs UTC)

### Responsive Testing
- Chrome DevTools (iPhone, iPad, desktop)
- Real device testing (if possible)
- Cross-browser (Chrome, Firefox, Safari)
- Touch interaction testing on tablet

---

## File Structure

```
/Users/soonjeongguan/Desktop/Repository/CLAUDECODE/NQPV2/
├── app.py                                (Updated with /dashboard route)
├── templates/
│   └── dashboard.html                    (Main dashboard template)
├── static/
│   ├── css/
│   │   └── dashboard.css                 (Dashboard styling)
│   └── js/
│       └── dashboard.js                  (Auto-refresh and data binding)
└── PHASE3_DASHBOARD_DESIGN.md            (This document)
```

---

## Implementation Checklist

- [ ] Create /templates directory and dashboard.html
- [ ] Create /static/css directory and dashboard.css
- [ ] Create /static/js directory and dashboard.js
- [ ] Add /dashboard route to app.py
- [ ] Implement MarketStatusTimer component
- [ ] Implement CurrentPriceDisplay component
- [ ] Implement ReferenceLevelsTable component
- [ ] Implement SessionRanges component
- [ ] Implement FibonacciPivots component
- [ ] Implement HourlyBlockSegmentation component
- [ ] Implement 75-second auto-refresh mechanism
- [ ] Add loading indicators and error handling
- [ ] Test responsive design on all breakpoints
- [ ] Add accessibility features (ARIA, semantic HTML)
- [ ] Test keyboard navigation and screen reader support
- [ ] Add comments and documentation
- [ ] Performance optimization and testing
- [ ] Deploy and monitor in production

---

## Deployment Notes

### Environment Configuration
- Ticker: NQ=F (default, can be parameterized)
- Refresh interval: 75 seconds (configurable via data attribute)
- Timezone: ET (Eastern Time, with UTC option)
- API base URL: / (relative, no prefix needed)

### Production Checklist
- [ ] Enable HTTPS only
- [ ] Set appropriate CORS headers
- [ ] Minify CSS and JavaScript
- [ ] Add Content Security Policy headers
- [ ] Configure caching headers appropriately
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting on API endpoints
- [ ] Test all error scenarios
- [ ] Document known limitations
- [ ] Create user documentation

---

## Future Enhancements

1. **Chart.js Integration:**
   - Price history chart (24h, 1w, 1m)
   - Volume analysis chart
   - Volatility visualization

2. **Advanced Filtering:**
   - Customize displayed components
   - Save dashboard preferences
   - Multiple ticker support

3. **Notifications:**
   - Price alerts (above/below threshold)
   - Session breakdown alerts
   - Status change notifications

4. **Dark Mode:**
   - System preference detection
   - Manual toggle
   - Automatic schedule (sunset/sunrise)

5. **Export/Reporting:**
   - PDF export
   - Data export (CSV)
   - Email reports

---

## References

- Bootstrap 5 Documentation: https://getbootstrap.com/docs/5.0/
- WCAG 2.1 Accessibility Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- Chart.js Documentation: https://www.chartjs.org/docs/latest/
- JavaScript Fetch API: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API
- ISO 8601 Date Format: https://en.wikipedia.org/wiki/ISO_8601

