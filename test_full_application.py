"""
Comprehensive Full Application Test Suite
Tests entire application: API endpoints + Dashboard UI
"""

import time
import requests
import json
import re
from typing import Dict, List, Tuple
from datetime import datetime

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

API_BASE_URL = "http://localhost:8080"
TICKER = "NQ=F"

class FullApplicationTester:
    def __init__(self):
        self.results = {
            "api_tests": [],
            "ui_tests": [],
            "integration_tests": []
        }
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.warnings = []

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}{text}{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    def print_test(self, test_name: str, status: bool, details: str = ""):
        """Print individual test result"""
        status_str = f"{GREEN}✓ PASS{RESET}" if status else f"{RED}✗ FAIL{RESET}"
        print(f"{status_str} | {test_name:<50} {details}")

        self.total_tests += 1
        if status:
            self.passed += 1
        else:
            self.failed += 1

    def test_api_endpoints(self):
        """Test all 16 API endpoints"""
        self.print_header("PHASE 2: API ENDPOINTS TESTS (16 endpoints)")

        endpoints = [
            # Market Status (3)
            (f"/api/market-status/{TICKER}", "Market Status - Full"),
            (f"/api/market-status/{TICKER}/is-open", "Market Status - Is Open"),
            (f"/api/market-status/{TICKER}/next-event", "Market Status - Next Event"),

            # Price (2)
            (f"/api/current-price/{TICKER}", "Current Price - Full"),
            (f"/api/current-price/{TICKER}/ohlc", "Current Price - OHLC"),

            # Reference Levels (3)
            (f"/api/reference-levels/{TICKER}", "Reference Levels - All"),
            (f"/api/reference-levels/{TICKER}/summary", "Reference Levels - Summary"),
            (f"/api/reference-levels/{TICKER}/closest", "Reference Levels - Closest"),

            # Session Ranges (3)
            (f"/api/session-ranges/{TICKER}", "Session Ranges - All"),
            (f"/api/session-ranges/{TICKER}/current", "Session Ranges - Current"),
            (f"/api/session-ranges/{TICKER}/previous", "Session Ranges - Previous"),

            # Fibonacci (3)
            (f"/api/fibonacci-pivots/{TICKER}", "Fibonacci Pivots - All"),
            (f"/api/fibonacci-pivots/{TICKER}/daily", "Fibonacci Pivots - Daily"),
            (f"/api/fibonacci-pivots/{TICKER}/weekly", "Fibonacci Pivots - Weekly"),

            # Hourly Blocks (3)
            (f"/api/hourly-blocks/{TICKER}", "Hourly Blocks - All"),
            (f"/api/hourly-blocks/{TICKER}/current-block", "Hourly Blocks - Current"),
            (f"/api/hourly-blocks/{TICKER}/summary", "Hourly Blocks - Summary"),
        ]

        for endpoint, description in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
                latency = (time.time() - start) * 1000

                success = response.status_code == 200
                if success:
                    data = response.json()
                    success = data.get('success', False)

                details = f"| {latency:.1f}ms | {response.status_code}"
                self.print_test(description, success, details)

                self.results["api_tests"].append({
                    "endpoint": endpoint,
                    "status": "pass" if success else "fail",
                    "latency_ms": latency,
                    "status_code": response.status_code
                })
            except Exception as e:
                self.print_test(description, False, f"| ERROR: {str(e)[:40]}")
                self.failed += 1

    def test_health_endpoints(self):
        """Test health and info endpoints"""
        self.print_header("HEALTH & INFO ENDPOINTS")

        endpoints = [
            ("/", "Root Info"),
            ("/health", "Health Check"),
            ("/dashboard", "Dashboard UI"),
        ]

        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
                success = response.status_code == 200

                details = f"| {response.status_code}"
                self.print_test(description, success, details)
                self.total_tests += 1
                if success:
                    self.passed += 1
                else:
                    self.failed += 1
            except Exception as e:
                self.print_test(description, False, f"| ERROR: {str(e)[:40]}")
                self.total_tests += 1
                self.failed += 1

    def test_dashboard_ui(self):
        """Test dashboard HTML structure and components"""
        self.print_header("PHASE 3: DASHBOARD UI TESTS")

        try:
            response = requests.get(f"{API_BASE_URL}/dashboard", timeout=10)

            # Test 1: Dashboard loads
            test1 = response.status_code == 200
            self.print_test("Dashboard loads (HTTP 200)", test1)

            # Test 2: Has HTML content
            html_content = response.text
            test2 = len(html_content) > 1000 and "<html" in html_content.lower()
            self.print_test("Dashboard has HTML content", test2)

            # Test 3: Bootstrap included
            test3 = "bootstrap" in html_content.lower()
            self.print_test("Bootstrap framework included", test3)

            # Test 4: Custom CSS included
            test4 = "dashboard.css" in html_content
            self.print_test("Custom dashboard.css included", test4)

            # Test 5: JavaScript included
            test5 = "dashboard.js" in html_content
            self.print_test("Dashboard JavaScript included", test5)

            # Test 6: Check for 6 components
            component_checks = {
                "MarketStatusTimer": "market-status" in html_content.lower(),
                "CurrentPriceDisplay": "current-price" in html_content.lower(),
                "ReferenceLevelsTable": "reference-levels" in html_content.lower(),
                "SessionRanges": "session-ranges" in html_content.lower(),
                "FibonacciPivots": "fibonacci" in html_content.lower(),
                "HourlyBlockSegmentation": "hourly-blocks" in html_content.lower() or "blocks" in html_content.lower(),
            }

            for component, found in component_checks.items():
                self.print_test(f"Component: {component}", found)

            # Test 7: Auto-refresh script present
            test7 = "75" in html_content and "refresh" in html_content.lower()
            self.print_test("75-second auto-refresh configured", test7)

            # Test 8: Check for responsive design
            test8 = "viewport" in html_content and "meta" in html_content
            self.print_test("Responsive viewport meta tag", test8)

            # Test 9: Loading indicators present
            test9 = "loading" in html_content.lower() or "spinner" in html_content.lower()
            self.print_test("Loading indicators present", test9)

            # Test 10: Error handling elements
            test10 = "error" in html_content.lower() or "alert" in html_content.lower()
            self.print_test("Error handling elements present", test10)

            self.total_tests += 10

        except Exception as e:
            self.print_test("Dashboard tests", False, f"| ERROR: {str(e)}")
            self.total_tests += 1

    def test_api_response_format(self):
        """Test API response JSON structure and format"""
        self.print_header("API RESPONSE FORMAT VALIDATION")

        try:
            # Test market status response format
            response = requests.get(f"{API_BASE_URL}/api/market-status/{TICKER}", timeout=10)
            data = response.json()

            test1 = "success" in data
            self.print_test("Response has 'success' field", test1)

            test2 = "ticker" in data
            self.print_test("Response has 'ticker' field", test2)

            test3 = "current_time_et" in data and "current_time_utc" in data
            self.print_test("Response has timezone fields (ET + UTC)", test3)

            # Test current price response
            response = requests.get(f"{API_BASE_URL}/api/current-price/{TICKER}", timeout=10)
            data = response.json()

            test4 = "current_price" in data and isinstance(data.get("current_price"), (int, float))
            self.print_test("Current price is numeric", test4)

            test5 = "change" in data and "change_percent" in data
            self.print_test("Price change metrics present", test5)

            # Test reference levels response
            response = requests.get(f"{API_BASE_URL}/api/reference-levels/{TICKER}", timeout=10)
            data = response.json()

            test6 = "reference_levels" in data and isinstance(data.get("reference_levels"), dict)
            self.print_test("Reference levels is a dictionary", test6)

            test7 = "signals" in data and isinstance(data.get("signals"), dict)
            self.print_test("Signals object present and valid", test7)

            test8 = "closest_level" in data
            self.print_test("Closest level identified", test8)

            # Test session ranges response
            response = requests.get(f"{API_BASE_URL}/api/session-ranges/{TICKER}", timeout=10)
            data = response.json()

            test9 = "current_session_ranges" in data or "session_ranges" in data
            self.print_test("Session ranges data present", test9)

            # Test fibonacci response
            response = requests.get(f"{API_BASE_URL}/api/fibonacci-pivots/{TICKER}", timeout=10)
            data = response.json()

            test10 = ("weekly_pivots" in data or "daily_pivots" in data)
            self.print_test("Fibonacci pivot levels present", test10)

        except Exception as e:
            self.print_test("Response format tests", False, f"| ERROR: {str(e)}")

    def test_timezone_handling(self):
        """Test timezone conversion and display"""
        self.print_header("TIMEZONE HANDLING VALIDATION")

        try:
            response = requests.get(f"{API_BASE_URL}/api/market-status/{TICKER}", timeout=10)
            data = response.json()

            # Test ET timezone
            et_time = data.get("current_time_et", "")
            test1 = "-05:00" in et_time or "-04:00" in et_time  # EST or EDT
            self.print_test("ET timezone offset correct (-05:00 or -04:00)", test1)

            # Test UTC timezone
            utc_time = data.get("current_time_utc", "")
            test2 = "+00:00" in utc_time
            self.print_test("UTC timezone offset correct (+00:00)", test2)

            # Test ISO 8601 format
            test3 = "T" in et_time and (":" in et_time or "-" in et_time)
            self.print_test("ISO 8601 format compliance", test3)

            # Test both times are present
            test4 = len(et_time) > 0 and len(utc_time) > 0
            self.print_test("Both ET and UTC times present", test4)

        except Exception as e:
            self.print_test("Timezone tests", False, f"| ERROR: {str(e)}")

    def test_error_handling(self):
        """Test error handling for invalid requests"""
        self.print_header("ERROR HANDLING VALIDATION")

        try:
            # Test 1: Invalid ticker
            response = requests.get(f"{API_BASE_URL}/api/current-price/INVALID", timeout=10)
            test1 = response.status_code == 400
            self.print_test("Invalid ticker returns 400", test1)

            # Test 2: Non-existent endpoint
            response = requests.get(f"{API_BASE_URL}/api/nonexistent", timeout=10)
            test2 = response.status_code == 404
            self.print_test("Non-existent endpoint returns 404", test2)

            # Test 3: Error response has proper format
            response = requests.get(f"{API_BASE_URL}/api/current-price/INVALID", timeout=10)
            if response.status_code >= 400:
                data = response.json()
                test3 = "success" in data and "error" in data
            else:
                test3 = False
            self.print_test("Error response has proper JSON format", test3)

        except Exception as e:
            self.print_test("Error handling tests", False, f"| ERROR: {str(e)}")

    def test_performance(self):
        """Test API response times"""
        self.print_header("PERFORMANCE METRICS")

        endpoints = [
            f"/api/market-status/{TICKER}",
            f"/api/current-price/{TICKER}",
            f"/api/reference-levels/{TICKER}",
            f"/api/session-ranges/{TICKER}",
            f"/api/fibonacci-pivots/{TICKER}",
            f"/api/hourly-blocks/{TICKER}",
        ]

        latencies = []

        for endpoint in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
                latency = (time.time() - start) * 1000
                latencies.append(latency)

                test = latency < 200
                status_str = f"| {latency:.1f}ms"
                self.print_test(endpoint.split('/')[-1], test, status_str)
            except:
                self.print_test(endpoint.split('/')[-1], False, "| TIMEOUT")

        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            print(f"\n{BOLD}Latency Summary:{RESET}")
            print(f"  Average: {BLUE}{avg_latency:.1f}ms{RESET}")
            print(f"  Min:     {GREEN}{min_latency:.1f}ms{RESET}")
            print(f"  Max:     {YELLOW if max_latency < 200 else RED}{max_latency:.1f}ms{RESET}")

    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")

        print(f"Total Tests Run: {self.total_tests}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.total_tests > 0:
            pass_rate = (self.passed / self.total_tests) * 100
            print(f"Pass Rate: {BLUE}{pass_rate:.1f}%{RESET}")

        if self.failed > 0:
            print(f"\n{RED}⚠ {self.failed} test(s) failed{RESET}")
        else:
            print(f"\n{GREEN}✓ All tests passed!{RESET}")

        # Test categories breakdown
        print(f"\n{BOLD}Test Categories:{RESET}")
        print(f"  API Endpoints: {len([t for t in self.results['api_tests'] if t['status'] == 'pass'])}/{len(self.results['api_tests'])}")

        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}\n")

    def run_all_tests(self):
        """Run complete test suite"""
        print(f"\n{BOLD}{BLUE}Starting Full Application Test Suite{RESET}")
        print(f"Target: {API_BASE_URL}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        try:
            self.test_health_endpoints()
            self.test_api_endpoints()
            self.test_api_response_format()
            self.test_timezone_handling()
            self.test_error_handling()
            self.test_performance()
            self.test_dashboard_ui()
        except Exception as e:
            print(f"\n{RED}Fatal error during testing: {e}{RESET}")
            return False

        self.print_summary()
        return self.failed == 0


def main():
    """Main test runner"""
    tester = FullApplicationTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
