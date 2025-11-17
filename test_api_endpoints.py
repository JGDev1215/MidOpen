"""
Comprehensive API Endpoint Testing
Tests all 6 endpoint groups for correct responses and latency
"""

import time
import requests
import json
from typing import Tuple, Dict, Any
from datetime import datetime

# API base URL
API_BASE_URL = "http://localhost:5000"
TICKER = "NQ=F"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Performance thresholds
LATENCY_THRESHOLD_MS = 200


class APITester:
    def __init__(self, base_url: str, ticker: str):
        self.base_url = base_url
        self.ticker = ticker
        self.results = {
            "market_status": [],
            "price": [],
            "reference_levels": [],
            "session_ranges": [],
            "fibonacci": [],
            "blocks": []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}{text}{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    def print_test(self, endpoint: str, status: bool, latency_ms: float, response_size: int):
        """Print test result"""
        status_str = f"{GREEN}✓ PASS{RESET}" if status else f"{RED}✗ FAIL{RESET}"
        latency_color = GREEN if latency_ms < LATENCY_THRESHOLD_MS else YELLOW
        latency_str = f"{latency_color}{latency_ms:.1f}ms{RESET}"

        print(f"{status_str} | {endpoint:<50} | {latency_str} | {response_size} bytes")

        self.total_tests += 1
        if status:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def test_endpoint(
        self,
        endpoint: str,
        group_name: str,
        expected_status: int = 200
    ) -> Tuple[bool, float, int]:
        """
        Test a single endpoint

        Returns:
            (success: bool, latency_ms: float, response_size: int)
        """
        url = f"{self.base_url}{endpoint}"

        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            latency = (time.time() - start_time) * 1000  # Convert to ms

            success = response.status_code == expected_status
            response_size = len(response.content)

            # Validate JSON response
            try:
                data = response.json()
                if expected_status == 200:
                    success = success and data.get('success', False)
            except json.JSONDecodeError:
                success = False

            self.results[group_name].append({
                "endpoint": endpoint,
                "status_code": response.status_code,
                "latency_ms": latency,
                "success": success,
                "response_size": response_size
            })

            return success, latency, response_size

        except requests.exceptions.Timeout:
            print(f"{RED}Timeout on {endpoint}{RESET}")
            return False, 5000.0, 0
        except requests.exceptions.ConnectionError:
            print(f"{RED}Connection error on {endpoint}{RESET}")
            return False, 0.0, 0
        except Exception as e:
            print(f"{RED}Error testing {endpoint}: {e}{RESET}")
            return False, 0.0, 0

    def test_market_status_endpoints(self):
        """Test market status endpoints"""
        self.print_header("1. MARKET STATUS ENDPOINTS")

        endpoints = [
            f"/api/market-status/{self.ticker}",
            f"/api/market-status/{self.ticker}/is-open",
            f"/api/market-status/{self.ticker}/next-event"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "market_status")
            self.print_test(endpoint, success, latency, size)

    def test_price_endpoints(self):
        """Test price endpoints"""
        self.print_header("2. PRICE ENDPOINTS")

        endpoints = [
            f"/api/current-price/{self.ticker}",
            f"/api/current-price/{self.ticker}/ohlc"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "price")
            self.print_test(endpoint, success, latency, size)

    def test_reference_levels_endpoints(self):
        """Test reference levels endpoints"""
        self.print_header("3. REFERENCE LEVELS ENDPOINTS")

        endpoints = [
            f"/api/reference-levels/{self.ticker}",
            f"/api/reference-levels/{self.ticker}/summary",
            f"/api/reference-levels/{self.ticker}/closest"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "reference_levels")
            self.print_test(endpoint, success, latency, size)

    def test_session_ranges_endpoints(self):
        """Test session ranges endpoints"""
        self.print_header("4. SESSION RANGES ENDPOINTS")

        endpoints = [
            f"/api/session-ranges/{self.ticker}",
            f"/api/session-ranges/{self.ticker}/current",
            f"/api/session-ranges/{self.ticker}/previous"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "session_ranges")
            self.print_test(endpoint, success, latency, size)

    def test_fibonacci_endpoints(self):
        """Test Fibonacci pivots endpoints"""
        self.print_header("5. FIBONACCI PIVOTS ENDPOINTS")

        endpoints = [
            f"/api/fibonacci-pivots/{self.ticker}",
            f"/api/fibonacci-pivots/{self.ticker}/daily",
            f"/api/fibonacci-pivots/{self.ticker}/weekly"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "fibonacci")
            self.print_test(endpoint, success, latency, size)

    def test_block_endpoints(self):
        """Test hourly block endpoints"""
        self.print_header("6. HOURLY BLOCK ENDPOINTS")

        endpoints = [
            f"/api/hourly-blocks/{self.ticker}",
            f"/api/hourly-blocks/{self.ticker}/current-block",
            f"/api/hourly-blocks/{self.ticker}/summary"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "blocks")
            self.print_test(endpoint, success, latency, size)

    def test_health_endpoints(self):
        """Test health check and index endpoints"""
        self.print_header("0. HEALTH & INFO ENDPOINTS")

        endpoints = [
            "/",
            "/health"
        ]

        for endpoint in endpoints:
            success, latency, size = self.test_endpoint(endpoint, "blocks")
            self.print_test(endpoint, success, latency, size)

    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")

        # Calculate statistics
        total_latency = {}
        for group, tests in self.results.items():
            if tests:
                latencies = [t["latency_ms"] for t in tests]
                total_latency[group] = {
                    "min": min(latencies),
                    "max": max(latencies),
                    "avg": sum(latencies) / len(latencies),
                    "count": len(tests)
                }

        print(f"Total Tests: {self.total_tests}")
        print(f"{GREEN}Passed: {self.passed_tests}{RESET}")
        print(f"{RED}Failed: {self.failed_tests}{RESET}")
        print(f"Pass Rate: {(self.passed_tests/self.total_tests*100):.1f}%\n")

        print(f"{BOLD}Latency Statistics:{RESET}")
        for group, stats in total_latency.items():
            print(f"\n{group.upper()}:")
            print(f"  Min:   {GREEN}{stats['min']:.1f}ms{RESET}")
            print(f"  Max:   {YELLOW}{stats['max']:.1f}ms{RESET}")
            print(f"  Avg:   {BLUE}{stats['avg']:.1f}ms{RESET}")
            print(f"  Tests: {stats['count']}")

        # Check latency threshold
        slow_endpoints = []
        for group, tests in self.results.items():
            for test in tests:
                if test["latency_ms"] > LATENCY_THRESHOLD_MS:
                    slow_endpoints.append({
                        "endpoint": test["endpoint"],
                        "latency_ms": test["latency_ms"]
                    })

        if slow_endpoints:
            print(f"\n{YELLOW}Endpoints exceeding {LATENCY_THRESHOLD_MS}ms threshold:{RESET}")
            for item in slow_endpoints:
                print(f"  {item['endpoint']}: {item['latency_ms']:.1f}ms")
        else:
            print(f"\n{GREEN}✓ All endpoints under {LATENCY_THRESHOLD_MS}ms{RESET}")

        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}\n")

    def run_all_tests(self):
        """Run all test groups"""
        print(f"\n{BOLD}{BLUE}Starting API Endpoint Tests{RESET}")
        print(f"Target: {API_BASE_URL}")
        print(f"Ticker: {self.ticker}")
        print(f"Threshold: {LATENCY_THRESHOLD_MS}ms")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        try:
            self.test_health_endpoints()
            self.test_market_status_endpoints()
            self.test_price_endpoints()
            self.test_reference_levels_endpoints()
            self.test_session_ranges_endpoints()
            self.test_fibonacci_endpoints()
            self.test_block_endpoints()
        except Exception as e:
            print(f"\n{RED}Error running tests: {e}{RESET}")
            return False

        self.print_summary()
        return self.failed_tests == 0


def main():
    """Main test runner"""
    tester = APITester(API_BASE_URL, TICKER)
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
