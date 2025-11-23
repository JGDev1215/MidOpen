/**
 * NQ=F Real-Time Market Data Dashboard
 * Auto-refresh and data binding logic
 * Refresh interval: 602 seconds (10 minutes 2 seconds)
 */

// Configuration
const CONFIG = {
    TICKER: 'NQ=F',
    REFRESH_INTERVAL: 602000, // 602 seconds (10 minutes 2 seconds)
    DATA_FRESHNESS_SYNC_INTERVAL: 5000, // Sync with server every 5 seconds
    COUNTDOWN_UPDATE_INTERVAL: 1000, // Update countdown display every 1 second
    TIMEOUT: 5000, // 5 seconds
    RETRY_DELAYS: [1000, 2000, 4000, 8000, 16000], // Exponential backoff
    API_BASE: '/api',
    TIMEZONE: 'ET'
};

// Global State
let dashboardState = {
    marketStatus: null,
    currentPrice: null,
    referenceLevels: null,
    sessionRanges: null,
    fibonacciPivots: null,
    hourlyBlocks: null,
    lastRefresh: null,
    isRefreshing: false,
    retryCount: 0
};

let refreshIntervalId = null;
let countdownIntervalId = null;
let clockIntervalId = null;
let dataFreshnessTimer = null; // DataFreshnessTimer instance

/**
 * DataFreshnessTimer Class
 * Manages the 602-second countdown timer and traffic light status
 * Syncs with backend /api/refresh-status endpoint
 */
class DataFreshnessTimer {
    constructor() {
        this.lastRefreshTime = null;
        this.totalInterval = 602000; // 602 seconds in milliseconds
        this.timerId = null;
        this.statusTimerId = null;

        // Thresholds (in seconds remaining)
        this.greenThreshold = 200;
        this.orangeThreshold = 60;

        // Color definitions
        this.colors = {
            green: { hex: '#10b981', name: 'Fresh Data', label: 'Green: Data is fresh' },
            orange: { hex: '#f59e0b', name: 'Aging Data', label: 'Orange: Data is aging' },
            red: { hex: '#ef4444', name: 'Stale Data', label: 'Red: Data is stale' }
        };

        this.initialize();
    }

    initialize() {
        // Start 1-second countdown ticker
        this.startCountdownTicker();

        // Sync with server every 5 seconds
        this.syncWithServer();
        this.statusTimerId = setInterval(() => this.syncWithServer(), CONFIG.DATA_FRESHNESS_SYNC_INTERVAL);

        // Initial display update
        this.updateDisplay();
    }

    startCountdownTicker() {
        if (this.timerId) clearInterval(this.timerId);

        this.updateDisplay(); // Initial call
        this.timerId = setInterval(() => this.updateDisplay(), CONFIG.COUNTDOWN_UPDATE_INTERVAL);
    }

    syncWithServer() {
        fetch(`${CONFIG.API_BASE}/refresh-status`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.lastRefreshTime = data.last_refresh_timestamp * 1000; // Convert to milliseconds
                    this.updateDisplay();
                }
            })
            .catch(error => console.error('Error syncing refresh status:', error));
    }

    updateDisplay() {
        const now = Date.now();
        const secondsElapsed = (now - this.lastRefreshTime) / 1000;
        const secondsRemaining = Math.max(0, 602 - secondsElapsed);
        const progressPercent = Math.min(100, (secondsElapsed / 602) * 100);

        // Update countdown timer display (MM:SS format)
        this.updateCountdownDisplay(secondsRemaining);

        // Update progress bar
        this.updateProgressBar(progressPercent);

        // Update traffic light color
        this.updateTrafficLight(secondsRemaining);

        // Update timestamps
        this.updateTimestamps();
    }

    updateCountdownDisplay(secondsRemaining) {
        const minutes = Math.floor(secondsRemaining / 60);
        const seconds = Math.floor(secondsRemaining % 60);
        const formatted = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        const display = document.getElementById('countdown-timer');
        if (display) {
            display.textContent = formatted;
        }
    }

    updateProgressBar(percent) {
        const bar = document.getElementById('freshness-progress-bar');
        const percentDisplay = document.getElementById('progress-percent');

        if (bar) {
            bar.style.width = percent + '%';

            // Update progress bar color
            if (percent < 33) {
                bar.className = 'progress-bar progress-fill-green';
            } else if (percent < 90) {
                bar.className = 'progress-bar progress-fill-orange';
            } else {
                bar.className = 'progress-bar progress-fill-red';
            }
        }

        if (percentDisplay) {
            percentDisplay.textContent = Math.round(percent) + '% elapsed';
        }
    }

    updateTrafficLight(secondsRemaining) {
        const indicator = document.getElementById('freshness-indicator');
        const statusLabel = document.getElementById('freshness-status-label');
        const statusName = document.getElementById('freshness-status-name');

        if (!indicator) return;

        let color;
        if (secondsRemaining > this.greenThreshold) {
            color = this.colors.green;
            indicator.className = 'light-indicator status-green';
        } else if (secondsRemaining > this.orangeThreshold) {
            color = this.colors.orange;
            indicator.className = 'light-indicator status-orange';
        } else {
            color = this.colors.red;
            indicator.className = 'light-indicator status-red';
        }

        if (statusLabel) statusLabel.textContent = color.name;
        if (statusName) statusName.textContent = color.label;
    }

    updateTimestamps() {
        if (!this.lastRefreshTime) return;

        const lastRefreshDt = new Date(this.lastRefreshTime);
        const nextRefreshDt = new Date(this.lastRefreshTime + 602000);

        const formatTime = (date) => {
            return new Intl.DateTimeFormat('en-US', {
                timeZone: 'America/New_York',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            }).format(date) + ' ET';
        };

        const lastDisplay = document.getElementById('last-refresh-display');
        const nextDisplay = document.getElementById('next-refresh-display');

        if (lastDisplay) lastDisplay.textContent = formatTime(lastRefreshDt);
        if (nextDisplay) nextDisplay.textContent = formatTime(nextRefreshDt);
    }

    resetTimer() {
        // Call backend to reset timer
        fetch(`${CONFIG.API_BASE}/refresh-status/reset`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.new_status) {
                    this.lastRefreshTime = data.new_status.last_refresh_timestamp * 1000;
                    this.updateDisplay();
                }
            })
            .catch(error => console.error('Error resetting timer:', error));
    }

    destroy() {
        if (this.timerId) clearInterval(this.timerId);
        if (this.statusTimerId) clearInterval(this.statusTimerId);
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initialized');

    // Initialize data freshness countdown timer
    dataFreshnessTimer = new DataFreshnessTimer();

    // Setup manual refresh button
    const manualRefreshBtn = document.getElementById('manual-refresh-btn');
    if (manualRefreshBtn) {
        manualRefreshBtn.addEventListener('click', () => {
            dataFreshnessTimer.resetTimer();
            refreshAllData(); // Also trigger data refresh
        });
    }

    // Initial data load
    refreshAllData();

    // Start clock and countdown updates (every second)
    startClockAndCountdown();

    // Setup auto-refresh timer
    setupAutoRefresh();

    // Setup error alert dismissal
    setupErrorHandling();
});

// Clock and Countdown Updates
function startClockAndCountdown() {
    updateClock();
    clockIntervalId = setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const etTime = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    }).format(now);
    
    // Update navbar clock
    const navbarTimeEl = document.getElementById('navbar-current-time');
    if (navbarTimeEl) {
        navbarTimeEl.textContent = etTime + ' ET';
    }
    
    // Update market status timer
    const marketTimeEl = document.getElementById('market-current-time');
    if (marketTimeEl) {
        marketTimeEl.textContent = etTime;
    }
    
    // Update countdown if we have market status data
    if (dashboardState.marketStatus && dashboardState.marketStatus.next_event) {
        updateCountdown(dashboardState.marketStatus.next_event);
    }
}

function updateCountdown(nextEvent) {
    const countdownDisplay = document.getElementById('countdown-display');
    const countdownType = document.getElementById('countdown-type');
    
    if (!countdownDisplay || !nextEvent) return;
    
    try {
        const eventTime = new Date(nextEvent.time_et);
        const now = new Date();
        const diffMs = eventTime - now;
        
        if (diffMs <= 0) {
            countdownDisplay.textContent = '0h 0m 0s';
            countdownType.textContent = 'Now';
            return;
        }
        
        const seconds = Math.floor((diffMs / 1000) % 60);
        const minutes = Math.floor((diffMs / (1000 * 60)) % 60);
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        
        countdownDisplay.textContent = hours + 'h ' + minutes + 'm ' + seconds + 's';
        countdownType.textContent = nextEvent.type === 'open' ? 'To Open' : 'To Close';
    } catch (error) {
        console.error('Error updating countdown:', error);
    }
}

// Auto-Refresh Setup
function setupAutoRefresh() {
    // Refresh every 602 seconds (10 minutes 2 seconds)
    refreshIntervalId = setInterval(() => {
        refreshAllData();
    }, CONFIG.REFRESH_INTERVAL);
}

// Data Fetching
async function fetchWithTimeout(url, timeout = CONFIG.TIMEOUT) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            signal: controller.signal,
            headers: {
                'Accept': 'application/json'
            }
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error('HTTP ' + response.status + ': ' + response.statusText);
        }
        
        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

async function refreshAllData() {
    if (dashboardState.isRefreshing) {
        console.log('Refresh already in progress');
        return;
    }
    
    dashboardState.isRefreshing = true;
    showRefreshIndicator();
    
    try {
        // Fetch all data in parallel
        const [marketStatus, currentPrice, referenceLevels, sessionRanges, fibonacciPivots, hourlyBlocks] = await Promise.allSettled([
            fetchWithTimeout(CONFIG.API_BASE + '/market-status/' + CONFIG.TICKER),
            fetchWithTimeout(CONFIG.API_BASE + '/current-price/' + CONFIG.TICKER),
            fetchWithTimeout(CONFIG.API_BASE + '/reference-levels/' + CONFIG.TICKER),
            fetchWithTimeout(CONFIG.API_BASE + '/session-ranges/' + CONFIG.TICKER),
            fetchWithTimeout(CONFIG.API_BASE + '/fibonacci-pivots/' + CONFIG.TICKER),
            fetchWithTimeout(CONFIG.API_BASE + '/hourly-blocks/' + CONFIG.TICKER)
        ]);
        
        // Process results
        if (marketStatus.status === 'fulfilled' && marketStatus.value.success) {
            dashboardState.marketStatus = marketStatus.value;
            updateMarketStatusComponent(marketStatus.value);
        }
        
        if (currentPrice.status === 'fulfilled' && currentPrice.value.success) {
            dashboardState.currentPrice = currentPrice.value;
            updatePriceComponent(currentPrice.value);
        }
        
        if (referenceLevels.status === 'fulfilled' && referenceLevels.value.success) {
            dashboardState.referenceLevels = referenceLevels.value;
            updateReferenceLevelsComponent(referenceLevels.value);
        }
        
        if (sessionRanges.status === 'fulfilled' && sessionRanges.value.success) {
            dashboardState.sessionRanges = sessionRanges.value;
            updateSessionRangesComponent(sessionRanges.value);
        }
        
        if (fibonacciPivots.status === 'fulfilled' && fibonacciPivots.value.success) {
            dashboardState.fibonacciPivots = fibonacciPivots.value;
            updateFibonacciComponent(fibonacciPivots.value);
        }
        
        if (hourlyBlocks.status === 'fulfilled' && hourlyBlocks.value.success) {
            dashboardState.hourlyBlocks = hourlyBlocks.value;
            updateHourlyBlocksComponent(hourlyBlocks.value);
        }
        
        // Update last refresh time
        dashboardState.lastRefresh = new Date();
        updateLastRefreshTime();
        
        // Reset retry count on success
        dashboardState.retryCount = 0;
        hideErrorAlert();
        
    } catch (error) {
        console.error('Error refreshing data:', error);
        handleRefreshError(error);
    } finally {
        dashboardState.isRefreshing = false;
        hideRefreshIndicator();
    }
}

// Component Updates
function updateMarketStatusComponent(data) {
    const statusBadge = document.getElementById('navbar-market-status');
    const marketStatusBadge = document.getElementById('market-status-badge');
    
    // Determine status class
    let statusClass = 'status-badge-loading';
    let statusIcon = 'fa-circle-notch';
    
    if (data.is_open) {
        statusClass = 'status-badge-open';
        statusIcon = 'fa-circle-check';
    } else if (data.is_maintenance) {
        statusClass = 'status-badge-maintenance';
        statusIcon = 'fa-exclamation-circle';
    } else if (data.is_closed) {
        statusClass = 'status-badge-closed';
        statusIcon = 'fa-circle-xmark';
    }
    
    // Update badges
    const newClass = statusClass;
    if (statusBadge) {
        statusBadge.className = 'badge ' + newClass;
        statusBadge.innerHTML = '<i class="fas ' + statusIcon + ' me-1"></i>' + data.status;
    }
    
    if (marketStatusBadge) {
        marketStatusBadge.className = 'badge ' + newClass;
        marketStatusBadge.innerHTML = '<i class="fas ' + statusIcon + ' me-2"></i>' + data.status;
        marketStatusBadge.classList.add('fade-update');
    }
    
    // Update hours of operation
    const hoursText = document.getElementById('hours-text');
    if (hoursText) {
        hoursText.textContent = data.hours_of_operation;
    }
}

function updatePriceComponent(data) {
    const priceEl = document.getElementById('current-price');
    const changeEl = document.getElementById('change-value');
    const changePercentEl = document.getElementById('change-percent-value');
    const changeSection = document.getElementById('price-change-section');
    const changeArrow = document.getElementById('change-arrow');
    const dailyLow = document.getElementById('daily-low');
    const dailyHigh = document.getElementById('daily-high');
    const lastUpdateEl = document.getElementById('last-update-time');
    const rangeIndicator = document.getElementById('range-indicator');
    
    // Update price
    if (priceEl) {
        priceEl.textContent = formatNumber(data.current_price);
        priceEl.classList.add('fade-update');
    }
    
    // Update change
    if (changeEl && changeSection) {
        const change = data.change;
        const changePercent = data.change_percent;
        
        changeEl.textContent = formatNumber(Math.abs(change));
        changePercentEl.textContent = Math.abs(changePercent).toFixed(2);
        
        if (change >= 0) {
            changeSection.classList.remove('negative');
            changeSection.classList.add('positive');
            changeArrow.className = 'fas fa-arrow-up me-2';
        } else {
            changeSection.classList.remove('positive');
            changeSection.classList.add('negative');
            changeArrow.className = 'fas fa-arrow-down me-2';
        }
    }
    
    // Update daily range
    if (dailyLow && dailyHigh && data.daily_low && data.daily_high) {
        dailyLow.textContent = formatNumber(data.daily_low);
        dailyHigh.textContent = formatNumber(data.daily_high);
        
        // Position range indicator
        const range = data.daily_high - data.daily_low;
        const positionPercent = range === 0 ? 50 : ((data.current_price - data.daily_low) / range) * 100;
        if (rangeIndicator) {
            rangeIndicator.style.left = Math.min(100, Math.max(0, positionPercent)) + '%';
        }
    }
    
    // Update last update time
    if (lastUpdateEl && data.last_update_time) {
        const updateTime = new Date(data.last_update_time);
        const timeStr = updateTime.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        lastUpdateEl.textContent = 'Last update: ' + timeStr + ' ET';
    }
}

function updateReferenceLevelsComponent(data) {
    const tbody = document.getElementById('reference-levels-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!data.reference_levels || !data.signals) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No data available</td></tr>';
        return;
    }
    
    // Sort levels by distance
    const levelEntries = Object.entries(data.reference_levels).map(function(entry) {
        const key = entry[0];
        const price = entry[1];
        const signal = data.signals[key];
        return {
            key: key,
            price: price,
            distance: signal ? signal.distance : 0,
            proximity: signal ? signal.proximity : 'UNKNOWN',
            isClosest: data.closest_level && data.closest_level.level === key
        };
    });
    
    levelEntries.sort(function(a, b) {
        return Math.abs(a.distance) - Math.abs(b.distance);
    });
    
    levelEntries.forEach(function(level) {
        const row = document.createElement('tr');
        if (level.isClosest) {
            row.classList.add('closest-level');
        }
        
        const proximityClass = 'proximity-' + level.proximity.toLowerCase();
        
        let html = '<td>' + formatLevelName(level.key) + '</td>' +
            '<td class="text-end">' + formatNumber(level.price) + '</td>' +
            '<td class="text-end">' + (level.distance > 0 ? '+' : '') + formatNumber(level.distance) + '</td>' +
            '<td class="text-center">' +
            '<span class="proximity-badge ' + proximityClass + '">' + level.proximity + '</span>' +
            '</td>';
        
        row.innerHTML = html;
        tbody.appendChild(row);
    });
}

function updateSessionRangesComponent(data) {
    const container = document.getElementById('sessions-container');
    if (!container || !data.current_session_ranges) return;
    
    container.innerHTML = '';
    
    const sessions = ['asian', 'london', 'ny_am', 'ny_pm'];
    const sessionNames = {
        asian: 'Asian',
        london: 'London',
        ny_am: 'NY AM',
        ny_pm: 'NY PM'
    };
    
    sessions.forEach(function(sessionKey) {
        const session = data.current_session_ranges[sessionKey];
        if (!session) return;
        
        const statusClass = session.within_range ? 'session-within-range' : 'session-above-range';
        const statusText = session.within_range ? 'Within Range' : (session.above_range ? 'Above' : 'Below');
        
        const positionPercent = session.range === 0 ? 50 : 
            ((session.current_price - session.low) / session.range) * 100;
        
        const card = document.createElement('div');
        card.className = 'session-card';
        
        let html = '<div class="session-name">' + sessionNames[sessionKey] + '</div>' +
            '<div class="session-time">' + session.name + '</div>' +
            '<div class="session-range-bar">' +
            '<div class="session-price-marker" style="left: ' + Math.min(100, Math.max(0, positionPercent)) + '%"></div>' +
            '</div>' +
            '<div class="session-values">' +
            '<span class="session-value-label">High: <strong>' + formatNumber(session.high) + '</strong></span>' +
            '<span class="session-value-label">Low: <strong>' + formatNumber(session.low) + '</strong></span>' +
            '</div>' +
            '<div class="session-range-info">' +
            '<div class="session-info-item">' +
            '<div class="session-info-label">Range</div>' +
            '<div class="session-info-value">' + formatNumber(session.range) + '</div>' +
            '</div>' +
            '<div class="session-info-item">' +
            '<div class="session-info-label">Bars</div>' +
            '<div class="session-info-value">' + session.bars_in_session + '</div>' +
            '</div>' +
            '</div>' +
            '<div class="session-status-indicator ' + statusClass + '">' + statusText + '</div>';
        
        card.innerHTML = html;
        container.appendChild(card);
    });
}

function updateFibonacciComponent(data) {
    const dailyContent = document.getElementById('daily-pivots-content');
    const weeklyContent = document.getElementById('weekly-pivots-content');
    
    if (dailyContent && data.daily_pivots) {
        dailyContent.innerHTML = renderPivotLevels(data.daily_pivots, data.closest_pivot, 'daily');
    }
    
    if (weeklyContent && data.weekly_pivots) {
        weeklyContent.innerHTML = renderPivotLevels(data.weekly_pivots, data.closest_pivot, 'weekly');
    }
}

function renderPivotLevels(pivots, closestPivot, timeframe) {
    const order = ['R3', 'R2', 'R1', 'PP', 'S1', 'S2', 'S3'];
    const pivotNames = {
        'R3': 'Resistance 3',
        'R2': 'Resistance 2',
        'R1': 'Resistance 1',
        'PP': 'Pivot Point',
        'S1': 'Support 1',
        'S2': 'Support 2',
        'S3': 'Support 3'
    };
    
    let html = '';
    
    order.forEach(function(level) {
        if (pivots[level] === undefined) return;
        
        const price = pivots[level];
        const distance = dashboardState.currentPrice ? 
            price - dashboardState.currentPrice.current_price : 0;
        
        const isClosest = closestPivot && closestPivot.level === level && closestPivot.timeframe === timeframe;
        const isResistance = ['R3', 'R2', 'R1'].includes(level);
        const isSupport = ['S1', 'S2', 'S3'].includes(level);
        const isPivot = level === 'PP';
        
        let levelClass = 'pivot-level';
        if (isResistance) levelClass += ' pivot-level-resistance';
        if (isPivot) levelClass += ' pivot-level-pivot';
        if (isSupport) levelClass += ' pivot-level-support';
        if (isClosest) levelClass += ' closest-pivot';
        
        html += '<div class="' + levelClass + '">' +
            '<div class="pivot-level-name">' + level + '</div>' +
            '<div class="pivot-level-info">' +
            '<div class="pivot-price">' + formatNumber(price) + '</div>' +
            '<div class="pivot-distance">' + (distance > 0 ? '+' : '') + formatNumber(distance) + '</div>' +
            '</div>' +
            '</div>';
    });
    
    return html;
}

function updateHourlyBlocksComponent(data) {
    if (!data.blocks || data.blocks.length === 0) return;
    
    // Update block progress bar
    const barsContainer = document.getElementById('blocks-bar');
    if (barsContainer) {
        barsContainer.innerHTML = '';
        
        const completedCount = data.blocks.filter(function(b) { return b.is_complete; }).length;
        
        data.blocks.forEach(function(block, index) {
            const blockEl = document.createElement('div');
            blockEl.className = 'block-item';
            
            if (block.is_complete) {
                blockEl.classList.add('completed');
            } else if (index === data.blocks.length - 1 || (!block.is_complete && data.blocks[index + 1] && data.blocks[index + 1].is_complete)) {
                blockEl.classList.add('active');
            } else {
                blockEl.classList.add('incomplete');
            }
            
            barsContainer.appendChild(blockEl);
        });
        
        // Update block count
        const countEl = document.getElementById('blocks-count');
        if (countEl) {
            const activeBlock = data.blocks.find(function(b, i) {
                return !b.is_complete && (i === 0 || data.blocks[i - 1].is_complete);
            });
            const blockNum = activeBlock ? activeBlock.block_num : data.blocks.length;
            countEl.textContent = blockNum + ' of 7 blocks';
        }
    }
    
    // Update current block OHLC
    if (data.current_block && data.current_block.ohlc) {
        const ohlcContainer = document.getElementById('current-block-ohlc');
        if (ohlcContainer) {
            const ohlc = data.current_block.ohlc;
            ohlcContainer.innerHTML = 
                '<div class="ohlc-value">' +
                '<div class="ohlc-label">Open</div>' +
                '<div class="ohlc-number">' + formatNumber(ohlc.open) + '</div>' +
                '</div>' +
                '<div class="ohlc-value">' +
                '<div class="ohlc-label">High</div>' +
                '<div class="ohlc-number">' + formatNumber(ohlc.high) + '</div>' +
                '</div>' +
                '<div class="ohlc-value">' +
                '<div class="ohlc-label">Low</div>' +
                '<div class="ohlc-number">' + formatNumber(ohlc.low) + '</div>' +
                '</div>' +
                '<div class="ohlc-value">' +
                '<div class="ohlc-label">Close</div>' +
                '<div class="ohlc-number">' + formatNumber(ohlc.close) + '</div>' +
                '</div>';
        }
        
        // Update block time
        const blockTimeEl = document.getElementById('block-time-text');
        if (blockTimeEl && data.current_block.start_time && data.current_block.end_time) {
            const startTime = new Date(data.current_block.start_time).toLocaleTimeString('en-US', {
                timeZone: 'America/New_York',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
            const endTime = new Date(data.current_block.end_time).toLocaleTimeString('en-US', {
                timeZone: 'America/New_York',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
            blockTimeEl.textContent = 'Block time: ' + startTime + ' - ' + endTime + ' ET';
        }
    }
}

// Utility Functions
function formatNumber(value) {
    if (value === null || value === undefined) return '--';
    return parseFloat(value).toFixed(2);
}

function formatLevelName(key) {
    const names = {
        'weekly_open': 'Weekly Open',
        'weekly_high': 'Weekly High',
        'weekly_low': 'Weekly Low',
        'daily_open': 'Daily Open',
        'daily_high': 'Daily High',
        'daily_low': 'Daily Low',
        'fourh_open': '4H Open',
        'fourh_high': '4H High',
        'fourh_low': '4H Low',
        'oneh_open': '1H Open',
        'oneh_high': '1H High',
        'oneh_low': '1H Low',
        'fiveteen_open': '15m Open',
        'fiveteen_high': '15m High',
        'fiveteen_low': '15m Low',
        'previous_close': 'Prev Close'
    };
    
    return names[key] || key.replace(/_/g, ' ').toUpperCase();
}

function updateLastRefreshTime() {
    const el = document.getElementById('last-refresh-time');
    if (!el || !dashboardState.lastRefresh) return;
    
    const timeStr = dashboardState.lastRefresh.toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    el.textContent = 'Last updated: ' + timeStr + ' ET';
}

// UI State Management
function showRefreshIndicator() {
    const indicator = document.getElementById('refresh-indicator');
    if (indicator) {
        indicator.classList.add('show');
    }
}

function hideRefreshIndicator() {
    const indicator = document.getElementById('refresh-indicator');
    if (indicator) {
        indicator.classList.remove('show');
    }
}

function showErrorAlert(message) {
    const alert = document.getElementById('error-alert');
    const messageEl = document.getElementById('error-message');
    
    if (alert && messageEl) {
        messageEl.textContent = message;
        alert.classList.add('show');
        alert.style.display = 'block';
    }
}

function hideErrorAlert() {
    const alert = document.getElementById('error-alert');
    if (alert) {
        alert.classList.remove('show');
        alert.style.display = 'none';
    }
}

function setupErrorHandling() {
    const alert = document.getElementById('error-alert');
    if (alert) {
        alert.addEventListener('close.bs.alert', function() {
            alert.style.display = 'none';
        });
    }
}

// Error Handling
function handleRefreshError(error) {
    console.error('Refresh error:', error);
    
    let message = 'Failed to refresh data';
    
    if (error.name === 'AbortError') {
        message = 'Data refresh timed out. Retrying...';
    } else if (error instanceof TypeError) {
        message = 'Network error. Retrying...';
    } else if (error instanceof Error) {
        message = 'Error: ' + error.message;
    }
    
    showErrorAlert(message);
    
    // Retry with exponential backoff
    if (dashboardState.retryCount < CONFIG.RETRY_DELAYS.length) {
        const delay = CONFIG.RETRY_DELAYS[dashboardState.retryCount];
        dashboardState.retryCount++;
        
        setTimeout(function() {
            refreshAllData();
        }, delay);
    }
}

// Cleanup
window.addEventListener('beforeunload', function() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    if (countdownIntervalId) clearInterval(countdownIntervalId);
    if (clockIntervalId) clearInterval(clockIntervalId);
});
