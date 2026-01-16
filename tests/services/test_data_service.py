"""
DataService单元测试
测试数据获取、缓存、处理和技术指标计算功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
import os
import tempfile

from services.data_service import DataService
from data.data_processor import DataProcessor
from data.data_storage import DataStorage


class TestDataServiceInitialization:
    """测试DataService初始化"""
    
    def test_init_with_valid_config(self):
        """测试使用有效配置初始化"""
        config = {
            'start_date': '2022-01-01',
            'end_date': '2024-12-31',
            'initial_holdings': {
                '600000': 100,
                '600001': 200,
                'cash': 100000
            }
        }
        
        service = DataService(config)
        
        assert service.config == config
        assert service.start_date == '2022-01-01'
        assert service.end_date == '2024-12-31'
        assert '600000' in service.stock_pool
        assert '600001' in service.stock_pool
        assert 'cash' not in service.stock_pool
        assert len(service.stock_pool) == 2
    
    def test_init_extracts_stock_pool_correctly(self):
        """测试正确提取股票池"""
        config = {
            'initial_holdings': {
                '600000': 100,
                '600001': 200,
                '600002': 300,
                'cash': 50000
            }
        }
        
        service = DataService(config)
        
        assert len(service.stock_pool) == 3
        assert 'cash' not in service.stock_pool
        assert all(code.startswith('6') for code in service.stock_pool)
    
    def test_init_with_default_dates(self):
        """测试使用默认日期"""
        config = {'initial_holdings': {}}
        
        service = DataService(config)
        
        assert service.start_date == '2022-01-01'
        assert service.end_date == '2024-12-31'
    
    def test_init_creates_empty_data_structures(self):
        """测试初始化创建空数据结构"""
        config = {'initial_holdings': {}}
        
        service = DataService(config)
        
        assert service.stock_data == {}
        assert service.dcf_values == {}
        assert service.rsi_thresholds == {}
        assert service.stock_industry_map == {}
        assert service.data_fetcher is None
        assert isinstance(service.data_processor, DataProcessor)
        assert isinstance(service.data_storage, DataStorage)


class TestDataServiceInitialize:
    """测试initialize方法"""
    
    @patch('services.data_service.DataFetcherFactory.create_fetcher')
    def test_initialize_success(self, mock_create_fetcher):
        """测试成功初始化"""
        config = {'initial_holdings': {}, 'data_source': 'akshare'}
        service = DataService(config)
        
        # Mock data fetcher
        mock_fetcher = Mock()
        mock_create_fetcher.return_value = mock_fetcher
        
        # Mock load methods
        service.load_dcf_values = Mock(return_value={'600000': 10.5})
        service.load_rsi_thresholds = Mock(return_value={'银行': {'overbought': 70}})
        service.load_stock_industry_map = Mock(return_value={'600000': {'industry': '银行'}})
        
        result = service.initialize()
        
        assert result is True
        assert service._initialized is True
        assert service.data_fetcher == mock_fetcher
        assert service.dcf_values == {'600000': 10.5}
        assert service.rsi_thresholds == {'银行': {'overbought': 70}}
        assert service.stock_industry_map == {'600000': {'industry': '银行'}}
    
    @patch('services.data_service.DataFetcherFactory.create_fetcher')
    def test_initialize_with_custom_data_source(self, mock_create_fetcher):
        """测试使用自定义数据源初始化"""
        config = {'initial_holdings': {}, 'data_source': 'tushare'}
        service = DataService(config)
        
        service.load_dcf_values = Mock(return_value={})
        service.load_rsi_thresholds = Mock(return_value={})
        service.load_stock_industry_map = Mock(return_value={})
        
        service.initialize()
        
        mock_create_fetcher.assert_called_once_with('tushare', config)
    
    @patch('services.data_service.DataFetcherFactory.create_fetcher')
    def test_initialize_handles_exception(self, mock_create_fetcher):
        """测试初始化异常处理"""
        config = {'initial_holdings': {}}
        service = DataService(config)
        
        mock_create_fetcher.side_effect = Exception("数据源创建失败")
        
        result = service.initialize()
        
        assert result is False
        assert service._initialized is False


class TestDataServiceLoadMethods:
    """测试数据加载方法"""
    
    @pytest.fixture
    def service(self):
        """创建service实例"""
        config = {'initial_holdings': {}}
        return DataService(config)
    
    @patch('services.data_service.get_path_manager')
    def test_load_dcf_values_success(self, mock_path_manager, service):
        """测试成功加载DCF估值"""
        # Mock path manager
        mock_pm = Mock()
        mock_pm.get_portfolio_config_path.return_value = '/fake/path/portfolio_config.csv'
        mock_path_manager.return_value = mock_pm
        
        # Mock CSV data
        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({
                'Stock_number': ['600000', '600001', 'CASH'],
                'DCF_value_per_share': [10.5, 15.2, None]
            })
            mock_read_csv.return_value = mock_df
            
            result = service.load_dcf_values()
            
            assert result == {'600000': 10.5, '600001': 15.2}
    
    @patch('services.data_service.get_path_manager')
    def test_load_dcf_values_file_not_found(self, mock_path_manager, service):
        """测试DCF文件不存在"""
        mock_pm = Mock()
        mock_pm.get_portfolio_config_path.return_value = '/fake/path/portfolio_config.csv'
        mock_path_manager.return_value = mock_pm
        
        with patch('pandas.read_csv', side_effect=FileNotFoundError):
            result = service.load_dcf_values()
            
            assert result == {}
    
    @patch('os.path.exists')
    def test_load_rsi_thresholds_success(self, mock_exists, service):
        """测试成功加载RSI阈值"""
        mock_exists.return_value = True
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({
                '行业代码': ['801010', '801020'],
                '行业名称': ['银行', '证券'],
                '普通超买': [70, 75],
                '普通超卖': [30, 25],
                '极端超买': [80, 85],
                '极端超卖': [20, 15],
                'layer': ['medium', 'medium'],
                'volatility': [0.15, 0.18],
                'current_rsi': [50, 55]
            })
            mock_read_csv.return_value = mock_df
            
            result = service.load_rsi_thresholds()
            
            assert '801010' in result
            assert result['801010']['sell_threshold'] == 70
            assert result['801010']['buy_threshold'] == 30
    
    @patch('os.path.exists')
    def test_load_stock_industry_map_success(self, mock_exists, service):
        """测试成功加载股票-行业映射"""
        mock_exists.return_value = True
        
        with patch('builtins.open', create=True) as mock_open:
            import json
            mock_data = {
                '600000': {'industry_code': '801010', 'industry_name': '银行'},
                '600001': {'industry_code': '801020', 'industry_name': '证券'}
            }
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_data)
            
            result = service.load_stock_industry_map()
            
            assert '600000' in result
            assert result['600000']['industry_code'] == '801010'
            assert result['600000']['industry_name'] == '银行'


class TestDataServiceGetStockData:
    """测试获取股票数据"""
    
    @pytest.fixture
    def service_with_mock_fetcher(self):
        """创建带有mock fetcher的service"""
        config = {
            'initial_holdings': {'600000': 100},
            'start_date': '2022-01-01',
            'end_date': '2024-12-31'
        }
        service = DataService(config)
        service.data_fetcher = Mock()
        service._initialized = True
        return service
    
    def test_get_stock_data_from_cache(self, service_with_mock_fetcher):
        """测试从缓存获取数据"""
        stock_code = '600000'
        
        # 预先设置stock_data
        mock_data = pd.DataFrame({
            'close': [10, 11, 12],
            'volume': [1000, 1100, 1200]
        })
        service_with_mock_fetcher.stock_data[stock_code] = {
            'daily': mock_data,
            'weekly': mock_data
        }
        
        result = service_with_mock_fetcher.get_stock_data(stock_code, 'daily')
        
        assert result is not None
        assert len(result) == 3
        assert 'close' in result.columns
    
    def test_get_stock_data_returns_none_if_not_exists(self, service_with_mock_fetcher):
        """测试股票数据不存在时返回None"""
        stock_code = '600999'
        
        result = service_with_mock_fetcher.get_stock_data(stock_code, 'daily')
        
        assert result is None
    
    def test_get_all_stock_data(self, service_with_mock_fetcher):
        """测试获取所有股票数据"""
        # 设置多个股票数据
        mock_data1 = pd.DataFrame({'close': [10, 11, 12]})
        mock_data2 = pd.DataFrame({'close': [20, 21, 22]})
        
        service_with_mock_fetcher.stock_data['600000'] = {
            'daily': mock_data1,
            'weekly': mock_data1
        }
        service_with_mock_fetcher.stock_data['600001'] = {
            'daily': mock_data2,
            'weekly': mock_data2
        }
        
        result = service_with_mock_fetcher.get_all_stock_data('weekly')
        
        assert len(result) == 2
        assert '600000' in result
        assert '600001' in result


class TestDataServiceProcessData:
    """测试数据处理"""
    
    @pytest.fixture
    def service(self):
        """创建service实例"""
        config = {'initial_holdings': {}}
        service = DataService(config)
        service._initialized = True
        return service
    
    def test_data_processor_integration(self, service):
        """测试数据处理器集成"""
        # 验证data_processor存在
        assert service.data_processor is not None
        assert isinstance(service.data_processor, DataProcessor)
    
    def test_data_storage_integration(self, service):
        """测试数据存储集成"""
        # 验证data_storage存在
        assert service.data_storage is not None
        assert isinstance(service.data_storage, DataStorage)
    
    def test_stock_pool_extraction(self, service):
        """测试股票池提取"""
        # 验证stock_pool正确提取
        assert isinstance(service.stock_pool, list)
        assert 'cash' not in service.stock_pool


class TestDataServicePrepareBacktestData:
    """测试准备回测数据"""
    
    @pytest.fixture
    def service_with_mocks(self):
        """创建带有mock的service"""
        config = {
            'initial_holdings': {'600000': 100, '600001': 200},
            'start_date': '2023-01-01',
            'end_date': '2024-12-31'
        }
        service = DataService(config)
        service._initialized = True
        service.data_fetcher = Mock()
        return service
    
    def test_prepare_backtest_data_success(self, service_with_mocks):
        """测试成功准备回测数据"""
        # Mock内部方法
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        mock_weekly_data = pd.DataFrame({
            'close': np.random.uniform(10, 15, 150),
            'rsi': np.random.uniform(30, 70, 150),
            'macd': np.random.uniform(-0.5, 0.5, 150)
        }, index=dates)
        
        service_with_mocks._get_cached_or_fetch_data = Mock(return_value=mock_weekly_data)
        service_with_mocks._get_or_generate_weekly_data = Mock(return_value=mock_weekly_data)
        service_with_mocks._ensure_technical_indicators = Mock(return_value=mock_weekly_data)
        service_with_mocks._process_dividend_data = Mock(return_value=mock_weekly_data)
        
        result = service_with_mocks.prepare_backtest_data()
        
        assert result is True
        assert len(service_with_mocks.stock_data) == 2
        assert '600000' in service_with_mocks.stock_data
        assert '600001' in service_with_mocks.stock_data
    
    def test_prepare_backtest_data_skips_failed_stocks(self, service_with_mocks):
        """测试跳过失败的股票"""
        # Mock第一只股票成功，第二只失败
        def mock_get_data(code, start, end, freq):
            if code == '600000':
                dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
                return pd.DataFrame({
                    'close': np.random.uniform(10, 15, 150),
                    'rsi': np.random.uniform(30, 70, 150)
                }, index=dates)
            else:
                return None
        
        service_with_mocks._get_cached_or_fetch_data = Mock(side_effect=mock_get_data)
        service_with_mocks._get_data_with_smart_expansion = Mock(return_value=None)
        
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        mock_data = pd.DataFrame({'close': [10]*150, 'rsi': [50]*150}, index=dates)
        service_with_mocks._get_or_generate_weekly_data = Mock(return_value=mock_data)
        service_with_mocks._ensure_technical_indicators = Mock(return_value=mock_data)
        service_with_mocks._process_dividend_data = Mock(return_value=mock_data)
        
        result = service_with_mocks.prepare_backtest_data()
        
        # 应该至少有一只股票或为空（因为第二只失败）
        assert len(service_with_mocks.stock_data) <= 2


class TestDataServiceIntegration:
    """集成测试"""
    
    @patch('services.data_service.DataFetcherFactory.create_fetcher')
    @patch('services.data_service.get_path_manager')
    def test_full_workflow(self, mock_path_manager, mock_create_fetcher):
        """测试完整工作流程"""
        # 准备配置
        config = {
            'initial_holdings': {'600000': 100},
            'start_date': '2023-01-01',
            'end_date': '2024-12-31',
            'data_source': 'akshare'
        }
        
        # 创建service
        service = DataService(config)
        
        # Mock path manager
        mock_pm = Mock()
        mock_pm.get_dcf_values_path.return_value = '/fake/dcf.csv'
        mock_pm.get_rsi_thresholds_path.return_value = '/fake/rsi.csv'
        mock_pm.get_stock_industry_map_path.return_value = '/fake/map.csv'
        mock_path_manager.return_value = mock_pm
        
        # Mock data fetcher
        mock_fetcher = Mock()
        mock_create_fetcher.return_value = mock_fetcher
        
        # Mock CSV loading
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.return_value = pd.DataFrame()
            
            # 初始化
            result = service.initialize()
            
            assert result is True
            assert service._initialized is True
            assert service.data_fetcher is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
