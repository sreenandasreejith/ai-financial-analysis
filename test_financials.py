import unittest
import os
import shutil
import json
from src.analysis.ratios import calculate_ratios
from src.analysis.risk_detector import detect_risks
from src.auth.models import init_db
from src.auth.manager import register_user, login_user, get_users_list

TEST_DB_PATH = "test_financial_analyzer.db"

class TestFinancialAnalysisAndAuth(unittest.TestCase):
    
    def setUp(self):
        # Initialize a fresh test database for each run
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        init_db(TEST_DB_PATH)

    def tearDown(self):
        # Cleanup test database
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_ratio_calculations(self):
        # Define mock metrics for two years (2025 and 2024)
        mock_metrics = {
            "years": [2025, 2024],
            "revenue": {"2025": 1000000.0, "2024": 800000.0},
            "net_income": {"2025": 150000.0, "2024": 80000.0},
            "assets": {"2025": 500000.0, "2024": 400000.0},
            "liabilities": {"2025": 200000.0, "2024": 180000.0},
            "equity": {"2025": 300000.0, "2024": 220000.0},
            "operating_expenses": {"2025": 600000.0, "2024": 520000.0},
            "operating_cash_flow": {"2025": 200000.0, "2024": 120000.0},
            "capex": {"2025": 50000.0, "2024": 40000.0},
        }
        
        ratios = calculate_ratios(mock_metrics)
        
        # Verify 2025 metrics
        ratios_2025 = ratios["2025"]
        self.assertEqual(ratios_2025["net_profit_margin_pct"], 15.0) # 150k / 1M
        self.assertEqual(ratios_2025["return_on_assets_pct"], 30.0) # 150k / 500k
        self.assertEqual(ratios_2025["return_on_equity_pct"], 50.0) # 150k / 300k
        self.assertEqual(ratios_2025["current_ratio"], 2.5) # 500k / 200k
        self.assertEqual(ratios_2025["debt_to_equity"], 0.67) # 200k / 300k (rounded to 2 decimals)
        self.assertEqual(ratios_2025["free_cash_flow"], 150000.0) # 200k - 50k

    def test_risk_detection_rules(self):
        # 1. Test Balance Sheet Discrepancy
        mock_metrics_unbalanced = {
            "years": [2025],
            "revenue": {"2025": 100000.0},
            "net_income": {"2025": 10000.0},
            "assets": {"2025": 200000.0},      # Assets = 200k
            "liabilities": {"2025": 80000.0},   # Liabilities = 80k
            "equity": {"2025": 100000.0},      # Equity = 100k (Total L+E = 180k, missing 20k)
            "operating_expenses": {"2025": 50000.0},
            "operating_cash_flow": {"2025": 15000.0},
            "capex": {"2025": 0.0},
        }
        ratios = calculate_ratios(mock_metrics_unbalanced)
        risks = detect_risks(mock_metrics_unbalanced, ratios)
        
        # Check if balance sheet anomaly is flagged
        has_bs_risk = any(r["category"] == "Balance Sheet Anomaly" for r in risks)
        self.assertTrue(has_bs_risk)
        
        # 2. Test Debt to Equity Risk (> 2.0)
        mock_metrics_high_leverage = {
            "years": [2025],
            "revenue": {"2025": 100000.0},
            "net_income": {"2025": 10000.0},
            "assets": {"2025": 300000.0},
            "liabilities": {"2025": 210000.0}, # Liab = 210k
            "equity": {"2025": 90000.0},       # Equity = 90k (Debt-to-equity = 2.33)
            "operating_expenses": {"2025": 50000.0},
            "operating_cash_flow": {"2025": 15000.0},
            "capex": {"2025": 0.0},
        }
        ratios_high = calculate_ratios(mock_metrics_high_leverage)
        risks_high = detect_risks(mock_metrics_high_leverage, ratios_high)
        
        has_solvency_risk = any(r["category"] == "Solvency Alert" and r["level"] == "High" for r in risks_high)
        self.assertTrue(has_solvency_risk)

    def test_user_authentication_flow(self):
        # Register a test user
        register_success = register_user("test_analyst", "securepass123", "User", TEST_DB_PATH)
        self.assertTrue(register_success)
        
        # Duplicated registration should fail
        register_fail = register_user("test_analyst", "diffpass456", "User", TEST_DB_PATH)
        self.assertFalse(register_fail)
        
        # Login with correct password
        user_logged_in = login_user("test_analyst", "securepass123", TEST_DB_PATH)
        self.assertIsNotNone(user_logged_in)
        self.assertEqual(user_logged_in["username"], "test_analyst")
        self.assertEqual(user_logged_in["role"], "User")
        
        # Login with incorrect password
        user_failed_login = login_user("test_analyst", "wrongpass", TEST_DB_PATH)
        self.assertIsNone(user_failed_login)

if __name__ == "__main__":
    unittest.main()
