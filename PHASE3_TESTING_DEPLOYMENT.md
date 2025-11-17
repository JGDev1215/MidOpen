# Phase 3: Dashboard Testing and Deployment Guide

**Project**: NQ=F Real-Time Market Data Dashboard  
**Phase**: Phase 3 - Frontend Dashboard  
**Document**: Testing and Deployment Guide  
**Last Updated**: 2025-11-17  

---

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Local Development Setup](#local-development-setup)
3. [Testing Procedures](#testing-procedures)
4. [Responsive Design Validation](#responsive-design-validation)
5. [Performance Testing](#performance-testing)
6. [Accessibility Testing](#accessibility-testing)
7. [Production Deployment](#production-deployment)
8. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Testing Strategy

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | E2E Tests | Manual Tests |
|-----------|-----------|------------------|-----------|-------------|
| MarketStatusTimer | Yes | Yes | Yes | Yes |
| CurrentPriceDisplay | Yes | Yes | Yes | Yes |
| ReferenceLevelsTable | Yes | Yes | Yes | Yes |
| SessionRanges | Yes | Yes | Yes | Yes |
| FibonacciPivots | Yes | Yes | Yes | Yes |
| HourlyBlocks | Yes | Yes | Yes | Yes |
| Auto-Refresh (75s) | Yes | Yes | Yes | Yes |
| Error Handling | Yes | Yes | Yes | Yes |
| Responsive Layout | No | Yes | Yes | Yes |
| Accessibility | No | No | Yes | Yes |

---

## Local Development Setup

### Prerequisites

```bash
# Check Python version (3.8+)
python --version

# Check pip
pip --version

# Check Node.js (optional, for build tools)
node --version
```

### Initial Setup

```bash
# Navigate to project directory
cd /Users/soonjeongguan/Desktop/Repository/CLAUDECODE/NQPV2

# Install Python dependencies (if not already installed)
pip install -r requirements.txt

# Verify Flask installation
python -c "import flask; print(flask.__version__)"
```

### Running the Application Locally

```bash
# Start the Flask development server
python app.py

# Output should show:
# * Running on http://0.0.0.0:5000
# * WARNING: This is a development server

# Access the dashboard
# Navigate to: http://localhost:5000/dashboard
```

### Directory Structure

```
/Users/soonjeongguan/Desktop/Repository/CLAUDECODE/NQPV2/
├── app.py                                    # Flask main app
├── templates/
│   └── dashboard.html                        # Dashboard UI
├── static/
│   ├── css/
│   │   └── dashboard.css                     # Dashboard styling
│   └── js/
│       └── dashboard.js                      # Dashboard logic
├── nasdaq_predictor/
│   ├── api/
│   │   └── routes/                           # API endpoints (6 groups)
│   ├── services/                             # Business logic
│   ├── data/                                 # Data fetching
│   └── utils/                                # Utilities
├── PHASE3_DASHBOARD_DESIGN.md                # Design documentation
└── PHASE3_TESTING_DEPLOYMENT.md              # This file
```

---

## Testing Procedures

### 1. Unit Tests - JavaScript Functions

#### Test File Structure (Not Yet Created)

```javascript
// tests/dashboard.test.js
describe('Dashboard Utilities', () => {
    describe('formatNumber()', () => {
        it('should format numbers to 2 decimal places', () => {
            expect(formatNumber(17245.567)).toBe('17245.57');
        });
        
        it('should handle null/undefined', () => {
            expect(formatNumber(null)).toBe('--');
            expect(formatNumber(undefined)).toBe('--');
        });
    });
    
    describe('formatLevelName()', () => {
        it('should convert key to readable label', () => {
            expect(formatLevelName('weekly_open')).toBe('Weekly Open');
            expect(formatLevelName('daily_high')).toBe('Daily High');
        });
    });
    
    describe('updateClock()', () => {
        it('should update ET time display every second', () => {
            // Mock DOM and verify time updates
        });
    });
});
```

### 2. Integration Tests - API Endpoints

#### Test Endpoints

```bash
# Test Market Status endpoint
curl -X GET "http://localhost:5000/api/market-status/NQ=F" \
  -H "Accept: application/json"

# Expected response:
{
  "success": true,
  "ticker": "NQ=F",
  "status": "OPEN|CLOSED|MAINTENANCE",
  "is_open": true/false,
  "current_time_et": "2025-11-17T10:45:30-05:00",
  "next_event": {
    "type": "close",
    "time_et": "2025-11-17T17:00:00-05:00",
    "countdown_seconds": 25200,
    "countdown_display": "7h 0m"
  }
}

# Test Current Price endpoint
curl -X GET "http://localhost:5000/api/current-price/NQ=F" \
  -H "Accept: application/json"

# Expected response:
{
  "success": true,
  "ticker": "NQ=F",
  "current_price": 17245.50,
  "change": 125.25,
  "change_percent": 0.73,
  "daily_high": 17250.0,
  "daily_low": 17200.0,
  "last_update_time": "2025-11-17T10:45:28-05:00"
}

# Test Reference Levels endpoint
curl -X GET "http://localhost:5000/api/reference-levels/NQ=F" \
  -H "Accept: application/json"

# Test Session Ranges endpoint
curl -X GET "http://localhost:5000/api/session-ranges/NQ=F" \
  -H "Accept: application/json"

# Test Fibonacci Pivots endpoint
curl -X GET "http://localhost:5000/api/fibonacci-pivots/NQ=F" \
  -H "Accept: application/json"

# Test Hourly Blocks endpoint
curl -X GET "http://localhost:5000/api/hourly-blocks/NQ=F" \
  -H "Accept: application/json"
```

#### Verify All Endpoints Return Success

```bash
# Quick test script
for endpoint in \
  "/api/market-status/NQ=F" \
  "/api/current-price/NQ=F" \
  "/api/reference-levels/NQ=F" \
  "/api/session-ranges/NQ=F" \
  "/api/fibonacci-pivots/NQ=F" \
  "/api/hourly-blocks/NQ=F"
do
  echo "Testing: $endpoint"
  curl -s -X GET "http://localhost:5000$endpoint" | jq '.success'
done
```

### 3. End-to-End Tests - Dashboard Loading

#### Manual E2E Testing Checklist

```bash
# 1. Open Dashboard
- Navigate to http://localhost:5000/dashboard
- Verify page loads without errors
- Check browser console for JS errors (F12 -> Console)
- Verify all components appear on screen

# 2. Verify Initial Data Load
- Market Status component should show:
  [ ] Current time in ET
  [ ] Market status badge (OPEN/CLOSED/MAINTENANCE)
  [ ] Countdown to next event
  [ ] Hours of operation text

- Current Price component should show:
  [ ] Large price display
  [ ] Change amount and percent
  [ ] Daily high/low with range bar
  [ ] Last update time

- Reference Levels should show:
  [ ] All 16 reference levels (or subset)
  [ ] Color-coded proximity badges
  [ ] Distance from current price
  [ ] Closest level highlighted

- Session Ranges should show:
  [ ] 4 trading sessions (Asian, London, NY AM, NY PM)
  [ ] High/low per session
  [ ] Range bar with price position
  [ ] Bar count indicator

- Fibonacci Pivots should show:
  [ ] Daily tab with R3-S3 levels
  [ ] Weekly tab with R3-S3 levels
  [ ] Distance from current price
  [ ] Color-coded resistance/support

- Hourly Blocks should show:
  [ ] 7-block progress bar
  [ ] Current block highlighted
  [ ] Block count (X of 7)
  [ ] Current block OHLC data

# 3. Test Auto-Refresh
- Set console timer: console.time('refresh')
- Wait for 75 seconds
- Verify data updates in all components
- Check console timer: console.timeEnd('refresh') = ~75000ms
- No errors should appear in console

# 4. Test Error Handling
- Open Network tab (F12 -> Network)
- Throttle network to 50% (DevTools -> Throttling)
- Refresh data manually (if button exists)
- Verify error message appears if API fails
- Verify fallback to cached data

# 5. Test Timezone Display
- Verify time shown in ET (Eastern Time)
- Cross-reference with system clock
- Check UTC offset (-05:00 in winter, -04:00 in summer)

# 6. Test Interaction
- Hover over components - verify hover state
- Click on Fibonacci tabs - verify tab switching
- Try keyboard navigation (Tab key)
- Verify focus indicators appear
```

---

## Responsive Design Validation

### Mobile Testing (320px - 575px)

#### iPhone SE (375px width)

```bash
# In Chrome DevTools:
# 1. Press F12 to open DevTools
# 2. Click Device Toolbar icon (or Ctrl+Shift+M)
# 3. Select "iPhone SE" from device list

# Verification Checklist:
[ ] Single-column layout displayed
[ ] Components stack vertically
[ ] No horizontal scrolling needed
[ ] Text is readable without zoom
[ ] Touch targets are 44x44px minimum
[ ] Navbar is visible and functional
[ ] All 6 components visible (with scrolling)
[ ] Charts/tables are responsive
[ ] Reference levels table scrollable
[ ] Buttons clickable with thumb
```

#### iPhone 12 Pro (390px width)

```bash
# Similar to iPhone SE, verify layout adjusts to 390px
[ ] All mobile verification points above
[ ] Additional spacing utilization
[ ] No layout shifts when scrolling
```

#### Samsung Galaxy (412px width)

```bash
# Verify Android device display
[ ] Android font rendering acceptable
[ ] Touch interactions smooth
[ ] Performance acceptable on lower-spec device
```

### Tablet Testing (576px - 991px)

#### iPad (768px width)

```bash
# In Chrome DevTools:
# 1. Select "iPad" from device list

# Verification Checklist:
[ ] 2-column layout for top components
[ ] Reference levels table spans full width
[ ] Session Ranges + Fibonacci Pivots side-by-side
[ ] Hourly Blocks full width
[ ] Optimal spacing and padding
[ ] Text sizes appropriate for viewing distance
[ ] No wasted whitespace
[ ] Touch targets appropriately sized
[ ] Navbar displays all elements
```

#### iPad Pro (1024px width)

```bash
# Verify larger tablet layout
[ ] 2-column layout maintained
[ ] Good use of screen real estate
[ ] No excessive margins
```

### Desktop Testing (992px+)

#### 1280px Viewport

```bash
# In Chrome DevTools:
# 1. Click on device selector
# 2. Type "1280x720" for custom size

# Verification Checklist:
[ ] 3-column top layout (Market Status | Price | Ref Levels)
[ ] 3-column bottom layout (Session | Fibonacci | Blocks)
[ ] All components visible without scrolling
[ ] Font sizes appropriate for desktop viewing
[ ] Hover states visible
[ ] White space balanced
[ ] No line wrapping issues in tables
```

#### 1920px Viewport (Full HD)

```bash
# Set custom size to 1920x1080

# Verification Checklist:
[ ] All components visible
[ ] No excessive stretching
[ ] Margins and padding scale appropriately
[ ] Data remains readable
[ ] No horizontal scrolling
```

#### 2560px Viewport (2K/4K)

```bash
# Set custom size to 2560x1440

# Verification Checklist:
[ ] Layout doesn't break at large widths
[ ] Font sizes remain readable (not tiny)
[ ] Components don't stretch excessively
[ ] Overall design maintains balance
```

### Cross-Browser Testing

#### Chrome/Chromium (Latest)

```bash
# Should be fully compatible
[ ] All features work
[ ] Animations smooth
[ ] No console errors
[ ] Performance excellent
```

#### Firefox (Latest)

```bash
# Verify Firefox compatibility
[ ] Layout correct
[ ] Flexbox/Grid working
[ ] Fetch API working
[ ] No Firefox-specific issues
```

#### Safari (Latest)

```bash
# Test on macOS Safari
[ ] Layout correct
[ ] CSS compatibility
[ ] JavaScript compatibility
[ ] Vendor prefixes if needed
```

#### Edge (Latest)

```bash
# Verify Edge compatibility
[ ] All features working
[ ] Animations smooth
[ ] No Edge-specific issues
```

---

## Performance Testing

### Load Time Measurement

```javascript
// In browser console
performance.mark('dashboard-start');
// ... after page fully loads
performance.mark('dashboard-end');
performance.measure('dashboard-load', 'dashboard-start', 'dashboard-end');
const measure = performance.getEntriesByName('dashboard-load')[0];
console.log('Dashboard load time: ' + measure.duration + 'ms');

// Expected: < 3000ms (3 seconds)
// Target: < 1500ms (1.5 seconds)
```

### Network Analysis

```bash
# 1. Open DevTools Network tab
# 2. Hard refresh (Ctrl+Shift+R)
# 3. Analyze waterfall chart

Expected metrics:
- HTML: < 100ms
- Bootstrap CSS: < 500ms
- Custom CSS: < 50ms
- Bootstrap JS: < 200ms
- Custom JS: < 100ms
- API calls (6 requests): < 3000ms total
- First Paint: < 1000ms
- Largest Contentful Paint (LCP): < 2500ms
```

### Bundle Size Analysis

```bash
Expected sizes (gzipped):
- bootstrap.css: ~30KB
- dashboard.css: ~8KB
- bootstrap.js: ~20KB
- dashboard.js: ~15KB
- Total: ~73KB
```

### Memory Usage

```javascript
// Monitor memory usage
if (performance.memory) {
    console.log('Heap Size: ' + (performance.memory.jsHeapSizeLimit / 1048576).toFixed(2) + ' MB');
    console.log('Heap Used: ' + (performance.memory.usedJSHeapSize / 1048576).toFixed(2) + ' MB');
    
    // Expected heap usage: < 20MB
}
```

---

## Accessibility Testing

### Keyboard Navigation

```bash
# 1. Open dashboard
# 2. Disable mouse (System Preferences -> Accessibility)
# 3. Use Tab key to navigate all interactive elements
# 4. Verify:

[ ] Can tab through all buttons/links
[ ] Tab order is logical (top-to-bottom, left-to-right)
[ ] Focus indicator always visible (2px outline)
[ ] Can activate buttons with Enter/Space
[ ] Can dismiss alerts with Escape
[ ] No keyboard traps (can always tab away)
```

### Screen Reader Testing (macOS)

```bash
# Enable VoiceOver
# System Preferences -> Accessibility -> VoiceOver

# Verify:
[ ] All text is readable
[ ] Headings are announced correctly
[ ] Data tables have proper headers
[ ] Images have alt text
[ ] Live regions announce updates (aria-live)
[ ] Form labels associated with inputs
[ ] Status badges clearly labeled
```

### Color Contrast Verification

```bash
# Tools:
# - WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
# - Chrome DevTools Lighthouse (Accessibility audit)

# Run Lighthouse audit:
# 1. F12 -> Lighthouse tab
# 2. Select "Accessibility"
# 3. Run audit
# 4. Expected score: > 90/100

# Manual checks:
[ ] Text on background has 4.5:1 contrast (AA)
[ ] Large text (18pt+) has 3:1 contrast (AA)
[ ] Color not sole indicator (icon + color)
[ ] Status badges have text labels
```

### ARIA Testing

```bash
# Verify ARIA implementation
[ ] aria-label on icon buttons
[ ] aria-live on auto-updating regions
[ ] aria-describedby for supplemental info
[ ] role attributes appropriate
[ ] No redundant ARIA
[ ] aria-current on active tab

# Use axe DevTools to check:
# Install: https://chrome.google.com/webstore
# Run axe scan - should have 0 violations
```

---

## Production Deployment

### Pre-Deployment Checklist

```bash
[ ] All tests passing
[ ] No console errors
[ ] Performance acceptable
[ ] Accessibility score > 90
[ ] Cross-browser testing complete
[ ] Responsive design validated
[ ] Code reviewed and approved
[ ] Documentation complete
[ ] Environment variables configured
[ ] Database migrations applied (if needed)
[ ] Error logging configured
[ ] Monitoring setup
[ ] Backup procedures documented
[ ] Rollback plan ready
```

### Environment Configuration

```python
# .env file (DO NOT COMMIT)
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=your-database-url
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
API_TIMEOUT=5000
REFRESH_INTERVAL=75000
```

### Deployment Steps

```bash
# 1. Build/prepare static assets (if using build tools)
# npm run build  # (optional)

# 2. Compress assets
gzip -9 static/css/dashboard.css
gzip -9 static/js/dashboard.js

# 3. Deploy to server
scp -r . user@server:/var/www/nq-dashboard/

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start Flask app with production server (NOT built-in)
# Option A: Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Option B: Using uWSGI
uwsgi --http :5000 --wsgi-file app.py --callable app --processes 4 --threads 2

# 6. Configure Nginx reverse proxy (recommended)
# See nginx-config.conf below

# 7. Setup SSL/TLS certificates (Let's Encrypt)
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# 8. Restart Nginx
systemctl restart nginx
```

### Nginx Configuration Example

```nginx
upstream nq_dashboard {
    server localhost:5000;
    server localhost:5001;
    server localhost:5002;
    server localhost:5003;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/json application/javascript;
    gzip_vary on;
    gzip_min_length 1024;

    location / {
        proxy_pass http://nq_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    location /static/ {
        alias /var/www/nq-dashboard/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location ~ ^/api/ {
        proxy_pass http://nq_dashboard;
        proxy_buffering off;
        proxy_cache_bypass $http_pragma $http_authorization;
        proxy_set_header Cache-Control "no-cache";
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Monitoring and Troubleshooting

### Application Monitoring

```bash
# Monitor application logs
tail -f /var/log/nq-dashboard/app.log

# Watch Gunicorn workers
ps aux | grep gunicorn

# Monitor system resources
watch -n 1 'free -h && df -h && ps aux | grep app.py'
```

### Common Issues and Solutions

#### Issue 1: Dashboard Not Loading

```
Symptom: Blank page or 404 error at /dashboard
Solution:
1. Verify Flask app is running: curl http://localhost:5000/
2. Check templates directory exists: ls templates/dashboard.html
3. Verify Flask can find templates:
   app = Flask(__name__, template_folder='templates')
4. Check Flask logs: tail -f app.log
5. Hard refresh browser: Ctrl+Shift+R
```

#### Issue 2: API Endpoints Not Responding

```
Symptom: Components show loading spinner indefinitely
Solution:
1. Test API directly: curl http://localhost:5000/api/market-status/NQ=F
2. Check API error response
3. Verify ticker is correct (NQ=F)
4. Check network tab (F12) for failed requests
5. Verify CORS headers: Access-Control-Allow-Origin: *
```

#### Issue 3: Data Not Updating After 75 Seconds

```
Symptom: Dashboard loads but never refreshes
Solution:
1. Check browser console for JS errors
2. Verify setInterval is running: check dashboardState.isRefreshing
3. Check network requests in DevTools
4. Verify API responses are valid JSON
5. Check fetchWithTimeout function working
6. Verify no API rate limiting
```

#### Issue 4: Styling Issues / Components Misaligned

```
Symptom: Layout broken on certain devices
Solution:
1. Verify CSS file loaded: F12 -> Network -> dashboard.css
2. Check for CSS errors: F12 -> Console
3. Verify Bootstrap CSS loaded
4. Check viewport meta tag in HTML
5. Test responsive design at specific breakpoints
6. Verify no CSS conflicts with other stylesheets
```

#### Issue 5: High Memory Usage / Slow Performance

```
Symptom: Dashboard becomes sluggish after time
Solution:
1. Check for memory leaks: performance.memory in console
2. Verify intervals are cleaned up on page unload
3. Check DOM for duplicate elements
4. Minimize CSS animations
5. Implement virtual scrolling for long tables
6. Monitor API call frequency
```

### Health Check Endpoint

```bash
# Monitor application health
curl http://localhost:5000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0"
}

# Create monitoring alert for non-200 response
```

### Log Analysis

```bash
# Search for errors in logs
grep ERROR /var/log/nq-dashboard/app.log

# Count API calls
grep "GET /api" /var/log/nq-dashboard/app.log | wc -l

# Monitor recent activity
tail -100 /var/log/nq-dashboard/app.log

# Filter by specific endpoint
grep "market-status" /var/log/nq-dashboard/app.log
```

---

## Testing Checklist

### Pre-Release Testing

- [ ] All 6 components load data successfully
- [ ] Auto-refresh works every 75 seconds
- [ ] Error handling shows proper messages
- [ ] Responsive design on mobile (320px)
- [ ] Responsive design on tablet (768px)
- [ ] Responsive design on desktop (1920px)
- [ ] Chrome browser compatible
- [ ] Firefox browser compatible
- [ ] Safari browser compatible
- [ ] All API endpoints return 200 OK
- [ ] Timezone displays correctly (ET)
- [ ] Market status badge shows correct status
- [ ] Price updates with color indicators
- [ ] Reference levels properly color-coded
- [ ] Session ranges visual indicators work
- [ ] Fibonacci pivot tabs switch correctly
- [ ] Hourly blocks progress bar displays
- [ ] Performance acceptable (< 3s load)
- [ ] No console errors
- [ ] Accessibility score > 90
- [ ] Keyboard navigation works
- [ ] Screen reader compatible

### Regression Testing After Updates

- [ ] Run full test suite
- [ ] Check responsive breakpoints
- [ ] Verify all API endpoints
- [ ] Test error handling
- [ ] Check performance metrics
- [ ] Validate accessibility
- [ ] Cross-browser testing

---

## References

- Bootstrap 5 Documentation: https://getbootstrap.com/docs/5.0/
- Chrome DevTools Guide: https://developer.chrome.com/docs/devtools/
- WCAG 2.1 Accessibility: https://www.w3.org/WAI/WCAG21/quickref/
- Lighthouse Audit: https://developers.google.com/web/tools/lighthouse
- axe DevTools: https://www.deque.com/axe/devtools/

---

## Support and Troubleshooting

For issues or questions:

1. Check browser console (F12)
2. Review application logs
3. Test API endpoints directly
4. Verify network connectivity
5. Check firewall rules
6. Review configuration files
7. Consult design documentation

