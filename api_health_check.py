"""
API Health Check for MDFDP Fraud Detection Modules
This script checks the health and availability of all fraud detection endpoints
without requiring authentication, focusing on system functionality.
"""

import requests
import json
import time
from datetime import datetime
import os

# Base URL for the Flask application
BASE_URL = "http://127.0.0.1:5000"

class MDFDPHealthChecker:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.health_results = {}
        
    def check_api_status(self):
        """Check overall API status"""
        print("Checking API Status...")
        try:
            response = requests.get(f"{self.base_url}/api/status")
            result = response.json()
            
            success = result.get("status") == "online"
            self.health_results["api_status"] = {
                "success": success,
                "status_code": response.status_code,
                "response": result,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"  API Status: {'✅ ONLINE' if success else '❌ OFFLINE'}")
            return success
        except Exception as e:
            print(f"  API Status: ❌ ERROR - {str(e)}")
            self.health_results["api_status"] = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return False
    
    def check_authentication_required(self):
        """Verify that fraud detection endpoints require authentication"""
        print("Verifying Authentication Protection...")
        
        endpoints_to_test = [
            ("/detect_upi", {"amount": 100}),
            ("/detect_credit", {"amount": 100}),
            ("/detect_spam", {"email_content": "test"}),
            ("/detect_phishing", {"url": "test.com"}),
            ("/detect_bot", {"username": "test"}),
        ]
        
        auth_protected_count = 0
        
        for endpoint, payload in endpoints_to_test:
            try:
                response = requests.post(f"{self.base_url}{endpoint}", json=payload)
                # Check if response indicates authentication is required
                if response.status_code == 401 or ('redirect' in response.text.lower() or 'login' in response.text.lower()):
                    auth_protected_count += 1
                else:
                    print(f"  Warning: {endpoint} may not require authentication")
            except Exception as e:
                print(f"  Error testing {endpoint}: {str(e)}")
        
        print(f"  Authentication Protection: {auth_protected_count}/{len(endpoints_to_test)} endpoints protected")
        return auth_protected_count == len(endpoints_to_test)
    
    def check_module_availability(self):
        """Check if all fraud detection modules are available in the status API"""
        print("Checking Module Availability...")
        try:
            response = requests.get(f"{self.base_url}/api/status")
            result = response.json()
            
            expected_modules = {
                "upi_fraud", "credit_card",
                "spam_email", "phishing_url", 
                "fake_profile"
            }
            
            available_modules = set()
            if "modules" in result:
                for module, status in result["modules"].items():
                    if status == "active":
                        available_modules.add(module)
            
            missing_modules = expected_modules - available_modules
            extra_modules = available_modules - expected_modules
            
            print(f"  Available modules: {len(available_modules)}/{len(expected_modules)}")
            if missing_modules:
                print(f"  Missing modules: {missing_modules}")
            if extra_modules:
                print(f"  Extra modules: {extra_modules}")
                
            all_available = len(missing_modules) == 0
            self.health_results["module_availability"] = {
                "success": all_available,
                "available_modules": list(available_modules),
                "expected_modules": list(expected_modules),
                "missing_modules": list(missing_modules),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"  Module Availability: {'✅ FULL' if all_available else '❌ PARTIAL'}")
            return all_available
            
        except Exception as e:
            print(f"  Module Availability: ❌ ERROR - {str(e)}")
            self.health_results["module_availability"] = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return False
    
    def check_routes_existence(self):
        """Check if all expected routes exist in the application"""
        print("Checking Route Existence...")
        
        routes_to_test = [
            "/api/status",
            "/login",
            "/signup", 
            "/verify_2fa",
            "/logout",
            "/detect_upi",
            "/detect_credit",
            "/detect_spam",
            "/detect_phishing",
            "/detect_bot",
            "/profile",
            "/analytics",
            "/security"
        ]
        
        accessible_routes = 0
        total_routes = len(routes_to_test)
        
        for route in routes_to_test:
            try:
                # Use HEAD request for efficiency
                response = requests.head(f"{self.base_url}{route}")
                if response.status_code in [200, 302, 401, 405]:  # 401 = auth required, 405 = method not allowed
                    accessible_routes += 1
                else:
                    print(f"  Route {route} returned status {response.status_code}")
            except Exception:
                print(f"  Route {route} is inaccessible")
        
        print(f"  Routes accessible: {accessible_routes}/{total_routes}")
        route_success = accessible_routes >= total_routes * 0.8  # Allow some flexibility
        
        self.health_results["routes_existence"] = {
            "success": route_success,
            "accessible_routes": accessible_routes,
            "total_routes": total_routes,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"  Route Existence: {'✅ GOOD' if route_success else '❌ ISSUES'}")
        return route_success
    def run_health_checks(self):
        """Run all health checks"""
        print("="*60)
        print("MDFDP HEALTH CHECK - FRAUD DETECTION PLATFORM")
        print("="*60)
        print(f"Checking: {self.base_url}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        # Run all health checks
        results = []
        results.append(self.check_api_status())
        results.append(self.check_authentication_required())
        results.append(self.check_module_availability())
        results.append(self.check_routes_existence())
        
        # Summary
        total_checks = len(results)
        passed_checks = sum(results)
        failed_checks = total_checks - passed_checks
        
        print("-"*60)
        print("HEALTH CHECK SUMMARY:")
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {failed_checks}")
        print(f"Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if passed_checks == total_checks:
            print("\n🎉 ALL HEALTH CHECKS PASSED!")
            print("✅ Platform is healthy and properly configured")
        elif passed_checks >= total_checks * 0.8:  # 80% threshold
            print("\n✅ PLATFORM IS HEALTHY WITH MINOR ISSUES")
        else:
            print(f"\n⚠️  PLATFORM HAS SIGNIFICANT ISSUES")
        
        print("="*60)
        
        # Save detailed results
        self.save_health_report()
        
        return passed_checks, failed_checks
    
    def save_health_report(self):
        """Save detailed health report to a JSON file"""
        filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.health_results, f, indent=2, default=str)
        print(f"Detailed health report saved to: {filename}")

if __name__ == "__main__":
    checker = MDFDPHealthChecker()
    checker.run_health_checks()
