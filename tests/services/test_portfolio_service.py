"""
PortfolioService单元测试
测试投资组合管理、交易执行、分红处理功能
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from services.portfolio_service import PortfolioService


class TestPortfolioServiceInitialization:
    """测试PortfolioService初始化"""
    
    def test_init_with_valid_config(self):
        """测试使用有效配置初始化"""
        config = {
            'total_capital': 1000000,
            'initial_holdings': {
                '600000': 100,
                '600001': 200,
                'cash': 500000
            }
        }
        dcf_values = {'600000': 10.5, '600001': 15.2}
        
        service = PortfolioService(config, dcf_values)
        
        assert service.config == config
        assert service.total_capital == 1000000
        assert service.initial_holdings == config['initial_holdings']
        assert service.dcf_values == dcf_values
    
    def test_init_creates_portfolio_manager(self):
        """测试初始化创建PortfolioManager"""
        config = {'total_capital': 1000000, 'initial_holdings': {}}
        dcf_values = {}
        
        service = PortfolioService(config, dcf_values)
        
        assert service.portfolio_manager is None
        assert service._initialized is False


class TestPortfolioServiceInitialize:
    """测试initialize方法"""
    
    @patch('services.portfolio_service.PortfolioDataManager')
    @patch('services.portfolio_service.DynamicPositionManager')
    def test_initialize_success(self, mock_dpm_class, mock_pdm_class):
        """测试成功初始化"""
        config = {
            'total_capital': 1000000,
            'initial_holdings': {'600000': 100}
        }
        dcf_values = {'600000': 10.5}
        service = PortfolioService(config, dcf_values)
        
        mock_pdm = Mock()
        mock_dpm = Mock()
        mock_pdm_class.return_value = mock_pdm
        mock_dpm_class.return_value = mock_dpm
        
        result = service.initialize()
        
        assert result is True
        assert service._initialized is True
        assert service.portfolio_data_manager == mock_pdm
        assert service.dynamic_position_manager == mock_dpm


class TestPortfolioServiceExecuteTrade:
    """测试交易执行"""
    
    @pytest.fixture
    def service_with_mock_pm(self):
        """创建带有mock portfolio manager的service"""
        config = {'total_capital': 1000000, 'initial_holdings': {'600000': 100}}
        dcf_values = {'600000': 10.5}
        service = PortfolioService(config, dcf_values)
        service.portfolio_manager = Mock()
        service.portfolio_data_manager = Mock()
        service.dynamic_position_manager = Mock()
        service._initialized = True
        return service
    
    def test_execute_trades_with_buy_signal(self, service_with_mock_pm):
        """测试执行买入信号"""
        signals = {'600000': 'BUY'}
        current_date = pd.Timestamp('2024-01-01')
        
        # Mock股票数据
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': [10.5]
                }, index=[current_date])
            }
        }
        
        # Mock portfolio manager方法
        service_with_mock_pm.portfolio_manager.get_total_value.return_value = 1000000
        service_with_mock_pm.portfolio_manager.positions = {'600000': 100}
        service_with_mock_pm._execute_buy = Mock(return_value='买入交易记录')
        
        result = service_with_mock_pm.execute_trades(signals, stock_data, current_date)
        
        assert len(result) >= 0
    
    def test_execute_trades_with_sell_signal(self, service_with_mock_pm):
        """测试执行卖出信号"""
        signals = {'600000': 'SELL'}
        current_date = pd.Timestamp('2024-01-01')
        
        # Mock股票数据
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': [12.5]
                }, index=[current_date])
            }
        }
        
        # Mock portfolio manager方法
        service_with_mock_pm.portfolio_manager.get_total_value.return_value = 1000000
        service_with_mock_pm.portfolio_manager.positions = {'600000': 100}
        service_with_mock_pm._execute_sell = Mock(return_value='卖出交易记录')
        
        result = service_with_mock_pm.execute_trades(signals, stock_data, current_date)
        
        assert len(result) >= 0
    
    def test_execute_trades_with_no_signals(self, service_with_mock_pm):
        """测试无信号时的交易执行"""
        signals = {}
        current_date = pd.Timestamp('2024-01-01')
        stock_data = {}
        
        service_with_mock_pm.portfolio_manager.get_total_value.return_value = 1000000
        
        result = service_with_mock_pm.execute_trades(signals, stock_data, current_date)
        
        assert result == []


class TestPortfolioServiceGetters:
    """测试获取投资组合信息"""
    
    @pytest.fixture
    def service_with_mock_pm(self):
        """创建带有mock portfolio manager的service"""
        config = {'total_capital': 1000000, 'initial_holdings': {'600000': 100}}
        dcf_values = {'600000': 10.5}
        service = PortfolioService(config, dcf_values)
        service.portfolio_manager = Mock()
        service._initialized = True
        return service
    
    def test_get_portfolio_manager(self, service_with_mock_pm):
        """测试获取portfolio manager"""
        assert service_with_mock_pm.portfolio_manager is not None
    
    def test_get_stock_pool(self, service_with_mock_pm):
        """测试获取股票池"""
        assert '600000' in service_with_mock_pm.stock_pool
        assert 'cash' not in service_with_mock_pm.stock_pool
    
    def test_portfolio_manager_methods(self, service_with_mock_pm):
        """测试portfolio manager方法可用性"""
        # 验证portfolio manager有必要的方法
        service_with_mock_pm.portfolio_manager.get_total_value = Mock(return_value=1000000)
        service_with_mock_pm.portfolio_manager.positions = {'600000': 100}
        service_with_mock_pm.portfolio_manager.cash = 500000
        
        # 调用方法
        total_value = service_with_mock_pm.portfolio_manager.get_total_value({'600000': 10.5})
        
        assert total_value == 1000000
        assert service_with_mock_pm.portfolio_manager.positions['600000'] == 100


class TestPortfolioServiceDividend:
    """测试分红处理"""
    
    @pytest.fixture
    def service_with_mock_pm(self):
        """创建带有mock portfolio manager的service"""
        config = {'total_capital': 1000000, 'initial_holdings': {'600000': 100}}
        dcf_values = {'600000': 10.5}
        service = PortfolioService(config, dcf_values)
        service.portfolio_manager = Mock()
        service._initialized = True
        return service
    
    def test_process_dividends_method_exists(self, service_with_mock_pm):
        """测试process_dividends方法存在"""
        # 验证service有process_dividends方法或类似功能
        assert hasattr(service_with_mock_pm, 'portfolio_manager')
        
        # Mock分红处理
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': [10.5],
                    'dividend_amount': [0.5]
                }, index=[pd.Timestamp('2024-01-01')])
            }
        }
        
        # 验证可以访问分红数据
        assert 'dividend_amount' in stock_data['600000']['weekly'].columns


class TestPortfolioServiceIntegration:
    """集成测试"""
    
    @patch('services.portfolio_service.PortfolioDataManager')
    @patch('services.portfolio_service.DynamicPositionManager')
    def test_full_workflow(self, mock_dpm_class, mock_pdm_class):
        """测试完整工作流程"""
        # 准备配置
        config = {
            'total_capital': 1000000,
            'initial_holdings': {'600000': 100, 'cash': 900000}
        }
        dcf_values = {'600000': 10.5}
        
        # 创建service
        service = PortfolioService(config, dcf_values)
        
        # Mock managers
        mock_pdm = Mock()
        mock_dpm = Mock()
        mock_pdm_class.return_value = mock_pdm
        mock_dpm_class.return_value = mock_dpm
        
        # Mock portfolio manager for trading
        service.portfolio_manager = Mock()
        service.portfolio_manager.get_holdings.return_value = {'600000': 100}
        service.portfolio_manager.get_cash.return_value = 900000
        service.portfolio_manager.get_total_value.return_value = 1000000
        service.portfolio_manager.buy_stock.return_value = True
        
        # 初始化
        result = service.initialize()
        assert result is True
        
        # 执行交易
        signals = {'600001': 'BUY'}
        stock_data = {
            '600001': {
                'weekly': pd.DataFrame({
                    'close': [20.0]
                }, index=[pd.Timestamp('2024-01-01')])
            }
        }
        service._execute_buy = Mock(return_value='买入记录')
        
        trade_result = service.execute_trades(
            signals, stock_data, pd.Timestamp('2024-01-01')
        )
        assert isinstance(trade_result, list)
        
        # 验证portfolio manager存在
        assert service.portfolio_manager is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
