#!/bin/bash

# Quick Application Test Script
# Tests all endpoints without Python dependencies

API_BASE="http://localhost:8080"
TICKER="NQ=F"

echo "========================================="
echo "NQ=F Real-Time Market Data Dashboard"
echo "COMPREHENSIVE APPLICATION TEST"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

test_endpoint() {
    local endpoint=$1
    local description=$2
    local method=${3:-GET}

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    local start_time=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" -X $method "${API_BASE}${endpoint}")
    local end_time=$(date +%s%N)

    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    local latency=$(( (end_time - start_time) / 1000000 ))

    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} | ${description} | ${latency}ms | HTTP $status_code"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC} | ${description} | HTTP $status_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

echo -e "${BLUE}=== HEALTH & INFO ENDPOINTS ===${NC}"
test_endpoint "/" "Root Info Endpoint"
test_endpoint "/health" "Health Check"
test_endpoint "/dashboard" "Dashboard UI"
echo ""

echo -e "${BLUE}=== MARKET STATUS ENDPOINTS ===${NC}"
test_endpoint "/api/market-status/$TICKER" "Market Status - Full"
test_endpoint "/api/market-status/$TICKER/is-open" "Market Status - Is Open"
test_endpoint "/api/market-status/$TICKER/next-event" "Market Status - Next Event"
echo ""

echo -e "${BLUE}=== CURRENT PRICE ENDPOINTS ===${NC}"
test_endpoint "/api/current-price/$TICKER" "Current Price - Full"
test_endpoint "/api/current-price/$TICKER/ohlc" "Current Price - OHLC"
echo ""

echo -e "${BLUE}=== REFERENCE LEVELS ENDPOINTS ===${NC}"
test_endpoint "/api/reference-levels/$TICKER" "Reference Levels - All"
test_endpoint "/api/reference-levels/$TICKER/summary" "Reference Levels - Summary"
test_endpoint "/api/reference-levels/$TICKER/closest" "Reference Levels - Closest"
echo ""

echo -e "${BLUE}=== SESSION RANGES ENDPOINTS ===${NC}"
test_endpoint "/api/session-ranges/$TICKER" "Session Ranges - All"
test_endpoint "/api/session-ranges/$TICKER/current" "Session Ranges - Current"
test_endpoint "/api/session-ranges/$TICKER/previous" "Session Ranges - Previous"
echo ""

echo -e "${BLUE}=== FIBONACCI PIVOTS ENDPOINTS ===${NC}"
test_endpoint "/api/fibonacci-pivots/$TICKER" "Fibonacci Pivots - All"
test_endpoint "/api/fibonacci-pivots/$TICKER/daily" "Fibonacci Pivots - Daily"
test_endpoint "/api/fibonacci-pivots/$TICKER/weekly" "Fibonacci Pivots - Weekly"
echo ""

echo -e "${BLUE}=== HOURLY BLOCKS ENDPOINTS ===${NC}"
test_endpoint "/api/hourly-blocks/$TICKER" "Hourly Blocks - All"
test_endpoint "/api/hourly-blocks/$TICKER/current-block" "Hourly Blocks - Current"
test_endpoint "/api/hourly-blocks/$TICKER/summary" "Hourly Blocks - Summary"
echo ""

echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((($PASSED_TESTS * 100) / $TOTAL_TESTS))
    echo "Pass Rate: ${BLUE}${PASS_RATE}%${NC}"
fi

echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠ Some tests failed${NC}"
    exit 1
fi
