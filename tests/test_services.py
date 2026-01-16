"""
服务层单元测试
测试DataService, SignalService, PortfolioService的核心功能
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_service import DataService
from services.signal_service import SignalService
from services.portfolio_service import PortfolioService
from config.csv_config_loader import load_backtest_settings, load_portfolio_config


class TestDataService(unittest.TestCase):
    """测试DataService"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.config = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
        cls.config['initial_holdings'] = load_portfolio_config('Input/portfolio_config.csv')
    
    def test_load_stock_industry_map(self):
        """测试股票-行业映射加载"""
        service = DataService(self.config)
        service.initialize()
        
        # 验证加载数量
        self.assertGreater(len(service.stock_industry_map), 5000, 
                          "应加载5000+条股票-行业映射")
        
        # 验证特定股票存在
        self.assertIn('002738', service.stock_industry_map, 
                     "应包含测试股票002738")
        
        # 验证映射结构
        stock_info = service.stock_industry_map['002738']
        self.assertEqual(stock_info['industry_code'], '801054', 
                        "002738应属于小金属行业")
        self.assertEqual(stock_info['industry_name'], '小金属')
    
    def test_load_rsi_thresholds(self):
        """测试RSI阈值加载"""
        service = DataService(self.config)
        service.initialize()
        
        # 验证加载数量
        self.assertGreater(len(service.rsi_thresholds), 100, 
                          "应加载100+个行业的RSI阈值")
        
        # 验证特定行业阈值
        self.assertIn('801054', service.rsi_thresholds, 
                     "应包含小金属行业阈值")
        
        # 验证阈值结构
        threshold = service.rsi_thresholds['801054']
        self.assertIn('buy_threshold', threshold)
        self.assertIn('sell_threshold', threshold)
        self.assertIn('extreme_buy_threshold', threshold)
        self.assertIn('extreme_sell_threshold', threshold)
    
    def test_load_dcf_values(self):
        """测试DCF估值加载"""
        service = DataService(self.config)
        service.initialize()
        
        # 验证加载
        self.assertGreater(len(service.dcf_values), 0, 
                          "应加载DCF估值数据")
        
        # 验证数据类型
        for code, value in service.dcf_values.items():
            self.assertIsInstance(value, (int, float), 
                                f"{code}的DCF估值应为数值类型")
            self.assertGreater(value, 0, 
                             f"{code}的DCF估值应大于0")


class TestSignalService(unittest.TestCase):
    """测试SignalService"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.config = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
        cls.config['initial_holdings'] = load_portfolio_config('Input/portfolio_config.csv')
        
        # 初始化DataService获取必要数据
        cls.data_service = DataService(cls.config)
        cls.data_service.initialize()
    
    def test_signal_service_initialization(self):
        """测试SignalService初始化"""
        signal_config = self.config.get('strategy_params', {})
        service = SignalService(
            signal_config,
            self.data_service.dcf_values,
            self.data_service.rsi_thresholds,
            self.data_service.stock_industry_map,
            self.data_service.stock_pool
        )
        
        self.assertTrue(service.initialize(), "SignalService应成功初始化")
        self.assertIsNotNone(service.signal_generator, "应创建SignalGenerator")
    
    def test_signal_generator_has_industry_map(self):
        """测试SignalGenerator是否正确接收行业映射"""
        signal_config = self.config.get('strategy_params', {})
        service = SignalService(
            signal_config,
            self.data_service.dcf_values,
            self.data_service.rsi_thresholds,
            self.data_service.stock_industry_map,
            self.data_service.stock_pool
        )
        service.initialize()
        
        # 验证SignalGenerator有行业映射
        self.assertGreater(len(service.signal_generator.stock_industry_map), 5000,
                          "SignalGenerator应有完整的行业映射")
        
        # 验证特定股票
        self.assertIn('002738', service.signal_generator.stock_industry_map,
                     "SignalGenerator应包含002738的行业映射")


class TestPortfolioService(unittest.TestCase):
    """测试PortfolioService"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.config = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
        cls.config['initial_holdings'] = load_portfolio_config('Input/portfolio_config.csv')
    
    def test_portfolio_service_initialization(self):
        """测试PortfolioService初始化"""
        dcf_values = {'601088': 50.0, '601225': 30.0}
        service = PortfolioService(self.config, dcf_values)
        
        # 创建模拟股票数据
        stock_data = {
            '601088': {
                'weekly': pd.DataFrame({
                    'close': [40.0, 41.0, 42.0],
                    'volume': [1000000, 1100000, 1200000]
                }, index=pd.date_range('2024-01-01', periods=3, freq='W'))
            }
        }
        
        start_date = pd.Timestamp('2024-01-01')
        result = service.initialize(stock_data, start_date, dcf_values)
        
        self.assertTrue(result, "PortfolioService应成功初始化")
        self.assertIsNotNone(service.portfolio_manager, "应创建PortfolioManager")
        self.assertIsNotNone(service.dynamic_position_manager, "应创建DynamicPositionManager")
        self.assertIsNotNone(service.cost_calculator, "应创建TransactionCostCalculator")


class TestIntegration(unittest.TestCase):
    """集成测试：验证服务间协作"""
    
    def test_services_consistency(self):
        """测试服务层与BacktestEngine的一致性"""
        from services.backtest_orchestrator import BacktestOrchestrator
        from backtest.backtest_engine import BacktestEngine
        
        config = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
        config['initial_holdings'] = load_portfolio_config('Input/portfolio_config.csv')
        
        # 运行Orchestrator
        orchestrator = BacktestOrchestrator(config)
        orchestrator.initialize()
        orchestrator.run_backtest()
        
        # 运行Engine（会显示废弃警告，这是预期的）
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            engine = BacktestEngine(config)
            engine.run_backtest()
        
        # 验证结果一致性
        orch_txns = len(orchestrator.portfolio_service.portfolio_manager.transaction_history)
        engine_txns = len(engine.portfolio_manager.transaction_history)
        
        self.assertEqual(orch_txns, engine_txns, 
                        f"交易次数应一致: Orchestrator={orch_txns}, Engine={engine_txns}")
        
        # 验证最终资金（允许极小误差）
        orch_cash = orchestrator.portfolio_service.portfolio_manager.cash
        engine_cash = engine.portfolio_manager.cash
        
        self.assertAlmostEqual(orch_cash, engine_cash, places=2,
                              msg=f"现金应一致: Orchestrator={orch_cash}, Engine={engine_cash}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestDataService))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalService))
    suite.addTests(loader.loadTestsFromTestCase(TestPortfolioService))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
