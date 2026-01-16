"""
SignalService单元测试
测试信号生成、详情记录、统计分析功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from services.signal_service import SignalService
from strategy.signal_generator import SignalGenerator


class TestSignalServiceInitialization:
    """测试SignalService初始化"""
    
    def test_init_with_valid_parameters(self):
        """测试使用有效参数初始化"""
        config = {
            'start_date': '2022-01-01',
            'end_date': '2024-12-31',
            'strategy_params': {
                'value_ratio_threshold': 0.8
            }
        }
        dcf_values = {'600000': 10.5, '600001': 15.2}
        rsi_thresholds = {
            '银行': {'overbought': 70, 'oversold': 30}
        }
        stock_industry_map = {
            '600000': {'industry': '银行', 'industry_level2': '银行'}
        }
        stock_pool = ['600000', '600001']
        
        service = SignalService(
            config,
            dcf_values,
            rsi_thresholds,
            stock_industry_map,
            stock_pool
        )
        
        assert service.config == config
        assert service.dcf_values == dcf_values
        assert service.rsi_thresholds == rsi_thresholds
        assert service.stock_industry_map == stock_industry_map
        assert service.stock_pool == stock_pool
        assert service.signal_generator is None
        assert service.signal_details == {}
    
    def test_init_with_signal_tracker(self):
        """测试使用信号跟踪器初始化"""
        config = {}
        signal_tracker = Mock()
        
        service = SignalService(
            config,
            {},
            {},
            {},
            [],
            signal_tracker
        )
        
        assert service.signal_tracker == signal_tracker
    
    def test_stock_pool_is_reference_not_copy(self):
        """测试stock_pool是引用而不是副本"""
        stock_pool = ['600000', '600001']
        service = SignalService({}, {}, {}, {}, stock_pool)
        
        # 修改原始列表
        stock_pool.append('600002')
        
        # 验证service中的stock_pool也被修改
        assert '600002' in service.stock_pool


class TestSignalServiceGenerateSignals:
    """测试信号生成功能"""
    
    @pytest.fixture
    def mock_signal_generator(self):
        """创建mock的SignalGenerator"""
        generator = Mock(spec=SignalGenerator)
        return generator
    
    @pytest.fixture
    def service_with_mock_generator(self, mock_signal_generator):
        """创建带有mock generator的service"""
        config = {'strategy_params': {}}
        service = SignalService(config, {}, {}, {}, ['600000', '600001'])
        service.signal_generator = mock_signal_generator
        service._initialized = True
        return service
    
    @pytest.fixture
    def sample_stock_data(self):
        """创建示例股票数据"""
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': np.random.uniform(10, 15, 150),
                    'rsi': np.random.uniform(30, 70, 150),
                    'macd': np.random.uniform(-0.5, 0.5, 150)
                }, index=dates)
            },
            '600001': {
                'weekly': pd.DataFrame({
                    'close': np.random.uniform(20, 25, 150),
                    'rsi': np.random.uniform(30, 70, 150),
                    'macd': np.random.uniform(-0.5, 0.5, 150)
                }, index=dates)
            }
        }
        return stock_data
    
    def test_generate_signals_with_buy_signal(self, service_with_mock_generator, sample_stock_data):
        """测试生成买入信号"""
        # 使用样本数据中实际存在的日期
        current_date = sample_stock_data['600000']['weekly'].index[130]
        
        # Mock返回买入信号
        service_with_mock_generator.signal_generator.generate_signal.return_value = {
            'signal': 'BUY',
            'reason': '测试买入信号',
            'scores': {'trend': 1, 'rsi': 1, 'macd': 1, 'extreme': 0}
        }
        
        signals = service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        assert '600000' in signals
        assert signals['600000'] == 'BUY'
        assert '600001' in signals
        assert signals['600001'] == 'BUY'
    
    def test_generate_signals_with_sell_signal(self, service_with_mock_generator, sample_stock_data):
        """测试生成卖出信号"""
        current_date = sample_stock_data['600000']['weekly'].index[130]
        
        service_with_mock_generator.signal_generator.generate_signal.return_value = {
            'signal': 'SELL',
            'reason': '测试卖出信号'
        }
        
        signals = service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        assert signals['600000'] == 'SELL'
        assert signals['600001'] == 'SELL'
    
    def test_generate_signals_filters_hold(self, service_with_mock_generator, sample_stock_data):
        """测试过滤HOLD信号"""
        current_date = sample_stock_data['600000']['weekly'].index[130]
        
        # 第一只股票返回BUY，第二只返回HOLD
        def side_effect(stock_code, data):
            if stock_code == '600000':
                return {'signal': 'BUY', 'reason': '买入'}
            else:
                return {'signal': 'HOLD', 'reason': '持有'}
        
        service_with_mock_generator.signal_generator.generate_signal.side_effect = side_effect
        
        signals = service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        assert '600000' in signals
        assert '600001' not in signals
    
    def test_generate_signals_records_details(self, service_with_mock_generator, sample_stock_data):
        """测试记录信号详情"""
        current_date = sample_stock_data['600000']['weekly'].index[130]
        
        signal_result = {
            'signal': 'BUY',
            'reason': '测试信号',
            'scores': {'trend': 1, 'rsi': 1, 'macd': 1, 'extreme': 0}
        }
        service_with_mock_generator.signal_generator.generate_signal.return_value = signal_result
        
        service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        # 验证信号详情被记录
        assert len(service_with_mock_generator.signal_details) > 0
        key = f"600000_{current_date.strftime('%Y-%m-%d')}"
        assert key in service_with_mock_generator.signal_details
        assert service_with_mock_generator.signal_details[key] == signal_result
    
    def test_generate_signals_skips_missing_stocks(self, service_with_mock_generator, sample_stock_data):
        """测试跳过缺失的股票"""
        current_date = sample_stock_data['600000']['weekly'].index[130]
        
        # 添加一个不存在的股票到stock_pool
        service_with_mock_generator.stock_pool.append('600999')
        
        service_with_mock_generator.signal_generator.generate_signal.return_value = {
            'signal': 'BUY'
        }
        
        signals = service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        # 验证不存在的股票被跳过
        assert '600999' not in signals
        assert len(signals) == 2
    
    def test_generate_signals_with_insufficient_data(self, service_with_mock_generator):
        """测试数据不足时的处理"""
        current_date = pd.Timestamp('2024-01-05')
        
        # 创建数据不足的股票数据（少于120条）
        dates = pd.date_range('2023-01-01', periods=50, freq='W-FRI')
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': np.random.uniform(10, 15, 50)
                }, index=dates)
            }
        }
        
        signals = service_with_mock_generator.generate_signals(stock_data, current_date)
        
        # 验证数据不足的股票被跳过
        assert '600000' not in signals
    
    def test_generate_signals_with_signal_tracker(self, service_with_mock_generator, sample_stock_data):
        """测试使用信号跟踪器"""
        current_date = sample_stock_data['600000']['weekly'].index[130]
        signal_tracker = Mock()
        service_with_mock_generator.signal_tracker = signal_tracker
        
        signal_result = {
            'signal': 'BUY',
            'reason': '测试信号'
        }
        service_with_mock_generator.signal_generator.generate_signal.return_value = signal_result
        
        service_with_mock_generator.generate_signals(sample_stock_data, current_date)
        
        # 验证信号被记录到tracker（应该被调用2次，每个股票一次）
        assert signal_tracker.record_signal.call_count == 2


class TestSignalServiceGetSignalDetails:
    """测试获取信号详情功能"""
    
    @pytest.fixture
    def service(self):
        """创建service实例"""
        return SignalService({}, {}, {}, {}, [])
    
    def test_get_signal_details_success(self, service):
        """测试成功获取信号详情"""
        stock_code = '600000'
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        stock_data = pd.DataFrame({
            'close': np.random.uniform(10, 15, 150),
            'rsi': np.random.uniform(30, 70, 150)
        }, index=dates)
        current_date = dates[130]
        
        # Mock signal_generator
        mock_generator = Mock()
        mock_generator.generate_signal.return_value = {
            'signal': 'BUY',
            'trigger_reason': '测试详情',
            'value_price_ratio': 0.75,
            'scores': {},
            'technical_indicators': {}
        }
        service.signal_generator = mock_generator
        
        details = service.get_signal_details(stock_code, stock_data, current_date)
        
        assert details is not None
        assert details['signal_type'] == 'BUY'
        assert details['trigger_reason'] == '测试详情'
        assert details['value_ratio'] == 0.75
    
    def test_get_signal_details_date_not_in_index(self, service):
        """测试日期不在索引中"""
        stock_code = '600000'
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        stock_data = pd.DataFrame({'close': [10] * 150}, index=dates)
        current_date = pd.Timestamp('2025-01-01')  # 不在索引中
        
        details = service.get_signal_details(stock_code, stock_data, current_date)
        
        assert details is None
    
    def test_get_signal_details_insufficient_history(self, service):
        """测试历史数据不足"""
        stock_code = '600000'
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        stock_data = pd.DataFrame({'close': [10] * 150}, index=dates)
        current_date = dates[50]  # 索引50，历史数据不足120
        
        details = service.get_signal_details(stock_code, stock_data, current_date)
        
        assert details is None


class TestSignalServiceGetStatistics:
    """测试获取统计信息功能"""
    
    def test_get_signal_statistics_empty(self):
        """测试空统计"""
        service = SignalService({}, {}, {}, {}, [])
        
        # 创建空的交易历史
        transaction_history = pd.DataFrame(columns=['trade_type', 'stock_code'])
        
        stats = service.get_signal_statistics(transaction_history)
        
        assert stats['global_stats']['total_signals'] == 0
        assert stats['global_stats']['total_buy_signals'] == 0
        assert stats['global_stats']['total_sell_signals'] == 0
    
    def test_get_signal_statistics_with_signals(self):
        """测试有信号的统计"""
        service = SignalService({}, {}, {}, {}, [])
        
        # 创建交易历史
        transaction_history = pd.DataFrame({
            'trade_type': ['buy', 'sell', 'buy', 'sell'],
            'stock_code': ['600000', '600001', '600002', '600003'],
            'trend_filter_met': [True, True, True, True],
            'rsi_oversold_met': [True, False, True, False],
            'macd_momentum_met': [True, True, False, False],
            'bollinger_volume_met': [False, True, True, False]
        })
        
        stats = service.get_signal_statistics(transaction_history)
        
        assert stats['global_stats']['total_signals'] == 4
        assert stats['global_stats']['total_buy_signals'] == 2
        assert stats['global_stats']['total_sell_signals'] == 2
        assert stats['dimension_stats']['trend_filter'] == 4
        assert stats['dimension_stats']['rsi_oversold'] == 2


class TestSignalServiceIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 准备配置和数据
        config = {
            'strategy_params': {
                'value_ratio_threshold': 0.8
            }
        }
        dcf_values = {'600000': 10.0}
        rsi_thresholds = {'银行': {'overbought': 70, 'oversold': 30}}
        stock_industry_map = {'600000': {'industry': '银行'}}
        stock_pool = ['600000']
        
        # 创建service
        service = SignalService(
            config,
            dcf_values,
            rsi_thresholds,
            stock_industry_map,
            stock_pool
        )
        
        # 初始化（使用mock的signal_generator）
        mock_generator = Mock(spec=SignalGenerator)
        service.signal_generator = mock_generator
        service._initialized = True
        
        # 准备股票数据
        dates = pd.date_range('2022-01-01', periods=150, freq='W-FRI')
        stock_data = {
            '600000': {
                'weekly': pd.DataFrame({
                    'close': np.random.uniform(10, 15, 150),
                    'rsi': np.random.uniform(30, 70, 150)
                }, index=dates)
            }
        }
        
        # 生成信号
        current_date = dates[130]
        mock_generator.generate_signal.return_value = {
            'signal': 'BUY',
            'reason': '集成测试信号'
        }
        
        signals = service.generate_signals(stock_data, current_date)
        
        # 验证结果
        assert '600000' in signals
        assert signals['600000'] == 'BUY'
        assert len(service.signal_details) > 0
        
        # 获取统计（使用实际的方法）
        transaction_history = pd.DataFrame({
            'trade_type': ['buy'],
            'stock_code': ['600000'],
            'trend_filter_met': [True],
            'rsi_oversold_met': [True],
            'macd_momentum_met': [True],
            'bollinger_volume_met': [False]
        })
        stats = service.get_signal_statistics(transaction_history)
        assert stats['global_stats']['total_signals'] == 1
        assert stats['global_stats']['total_buy_signals'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
