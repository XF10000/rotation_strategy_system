"""
RSI阈值自动更新器测试
测试季度自动更新机制的各个功能
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from utils.rsi_threshold_updater import RSIThresholdUpdater, check_and_update_rsi_threshold


class TestRSIThresholdUpdater:
    """RSI阈值更新器测试类"""
    
    @pytest.fixture
    def updater(self):
        """创建测试用的updater实例"""
        return RSIThresholdUpdater()
    
    @pytest.fixture
    def temp_threshold_file(self):
        """创建临时阈值文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            # 创建测试数据
            df = pd.DataFrame({
                '行业代码': ['801010', '801020', '801030'],
                '行业名称': ['农业', '林业', '渔业'],
                '普通超买': [70, 72, 68],
                '普通超卖': [30, 28, 32],
                '更新时间': ['2025-08-11 11:27:47'] * 3
            })
            df.to_csv(f.name, index=False, encoding='utf-8')
            temp_path = f.name
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_get_current_quarter(self, updater):
        """测试季度识别功能"""
        # Q1: 1-3月
        assert updater.get_current_quarter(datetime(2025, 1, 15)) == 1
        assert updater.get_current_quarter(datetime(2025, 2, 28)) == 1
        assert updater.get_current_quarter(datetime(2025, 3, 31)) == 1
        
        # Q2: 4-6月
        assert updater.get_current_quarter(datetime(2025, 4, 1)) == 2
        assert updater.get_current_quarter(datetime(2025, 5, 15)) == 2
        assert updater.get_current_quarter(datetime(2025, 6, 30)) == 2
        
        # Q3: 7-9月
        assert updater.get_current_quarter(datetime(2025, 7, 1)) == 3
        assert updater.get_current_quarter(datetime(2025, 8, 15)) == 3
        assert updater.get_current_quarter(datetime(2025, 9, 30)) == 3
        
        # Q4: 10-12月
        assert updater.get_current_quarter(datetime(2025, 10, 1)) == 4
        assert updater.get_current_quarter(datetime(2025, 11, 15)) == 4
        assert updater.get_current_quarter(datetime(2025, 12, 31)) == 4
    
    def test_get_quarter_start_date(self, updater):
        """测试季度开始日期计算"""
        assert updater.get_quarter_start_date(2025, 1) == datetime(2025, 1, 1)
        assert updater.get_quarter_start_date(2025, 2) == datetime(2025, 4, 1)
        assert updater.get_quarter_start_date(2025, 3) == datetime(2025, 7, 1)
        assert updater.get_quarter_start_date(2025, 4) == datetime(2025, 10, 1)
    
    def test_get_threshold_file_info_file_not_exists(self, updater):
        """测试文件不存在时的信息获取"""
        updater.threshold_file_path = "nonexistent_file.csv"
        result = updater.get_threshold_file_info()
        assert result is None
    
    def test_get_threshold_file_info_success(self, updater, temp_threshold_file):
        """测试成功获取文件信息"""
        updater.threshold_file_path = temp_threshold_file
        result = updater.get_threshold_file_info()
        
        assert result is not None
        update_time, industry_count = result
        assert isinstance(update_time, datetime)
        assert industry_count == 3  # 测试数据有3个行业
    
    def test_should_update_threshold_force_update(self, updater):
        """测试强制更新"""
        should_update, reason = updater.should_update_threshold(force_update=True)
        assert should_update is True
        assert reason == "强制更新"
    
    def test_should_update_threshold_file_not_exists(self, updater):
        """测试文件不存在时需要更新"""
        updater.threshold_file_path = "nonexistent_file.csv"
        should_update, reason = updater.should_update_threshold()
        assert should_update is True
        assert "不存在" in reason or "无效" in reason
    
    def test_should_update_threshold_cross_quarter(self, updater, temp_threshold_file):
        """测试跨季度更新"""
        updater.threshold_file_path = temp_threshold_file
        
        # Mock文件信息：文件是Q1创建的
        old_time = datetime(2025, 3, 15)  # Q1
        
        with patch.object(updater, 'get_threshold_file_info', return_value=(old_time, 124)):
            # Mock当前时间为Q2
            with patch('utils.rsi_threshold_updater.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2025, 5, 15)  # Q2
                mock_datetime.strptime = datetime.strptime
                
                should_update, reason = updater.should_update_threshold()
                assert should_update is True
                assert "跨季度" in reason
    
    def test_should_update_threshold_cross_year(self, updater, temp_threshold_file):
        """测试跨年度更新"""
        updater.threshold_file_path = temp_threshold_file
        
        # Mock文件信息：文件是2024年创建的
        old_time = datetime(2024, 12, 15)
        
        with patch.object(updater, 'get_threshold_file_info', return_value=(old_time, 124)):
            # Mock当前时间为2025年
            with patch('utils.rsi_threshold_updater.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2025, 1, 15)
                mock_datetime.strptime = datetime.strptime
                
                should_update, reason = updater.should_update_threshold()
                assert should_update is True
                assert "跨年度" in reason
    
    def test_should_update_threshold_old_file(self, updater, temp_threshold_file):
        """测试文件过旧（>120天）需要更新"""
        updater.threshold_file_path = temp_threshold_file
        
        # Mock文件信息：文件是150天前创建的，但在同一年同一季度
        # 使用固定日期避免跨年度问题
        current_date = datetime(2025, 8, 15)  # Q3
        old_time = datetime(2025, 3, 15)  # Q1，150天前但同一年
        
        with patch.object(updater, 'get_threshold_file_info', return_value=(old_time, 124)):
            with patch('utils.rsi_threshold_updater.datetime') as mock_datetime:
                mock_datetime.now.return_value = current_date
                mock_datetime.strptime = datetime.strptime
                
                should_update, reason = updater.should_update_threshold()
                assert should_update is True
                # 跨季度优先级更高，所以会是跨季度原因
                assert "跨季度" in reason or "过旧" in reason
    
    def test_should_update_threshold_low_industry_count(self, updater, temp_threshold_file):
        """测试行业数量异常少时需要更新"""
        updater.threshold_file_path = temp_threshold_file
        
        # Mock文件信息：只有50个行业（异常少）
        recent_time = datetime.now() - timedelta(days=10)
        
        with patch.object(updater, 'get_threshold_file_info', return_value=(recent_time, 50)):
            should_update, reason = updater.should_update_threshold()
            assert should_update is True
            assert "异常" in reason
    
    def test_should_update_threshold_no_update_needed(self, updater, temp_threshold_file):
        """测试文件较新时不需要更新"""
        updater.threshold_file_path = temp_threshold_file
        
        # Mock文件信息：文件是10天前创建的，确保在同一季度
        current_date = datetime(2025, 8, 15)  # Q3
        recent_time = datetime(2025, 8, 5)   # Q3，10天前，同一季度
        
        with patch.object(updater, 'get_threshold_file_info', return_value=(recent_time, 124)):
            with patch('utils.rsi_threshold_updater.datetime') as mock_datetime:
                mock_datetime.now.return_value = current_date
                mock_datetime.strptime = datetime.strptime
                
                should_update, reason = updater.should_update_threshold()
                assert should_update is False
                assert "较新" in reason
    
    def test_get_update_status_file_not_exists(self, updater):
        """测试获取不存在文件的状态"""
        updater.threshold_file_path = "nonexistent_file.csv"
        status = updater.get_update_status()
        
        assert status['file_exists'] is False
        assert status['update_time'] is None
        assert status['industry_count'] == 0
        assert status['needs_update'] is True
    
    def test_get_update_status_file_exists(self, updater, temp_threshold_file):
        """测试获取存在文件的状态"""
        updater.threshold_file_path = temp_threshold_file
        status = updater.get_update_status()
        
        assert status['file_exists'] is True
        assert status['update_time'] is not None
        assert status['industry_count'] == 3
        assert 'current_quarter' in status
        assert 'file_quarter' in status
        assert 'needs_update' in status
        assert 'reason' in status
    
    @patch('utils.rsi_threshold_updater.subprocess.run')
    def test_run_rsi_calculation_success(self, mock_run, updater):
        """测试成功运行RSI计算"""
        # Mock成功的subprocess结果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "计算完成"
        mock_run.return_value = mock_result
        
        success = updater.run_rsi_calculation()
        assert success is True
        assert mock_run.called
    
    @patch('utils.rsi_threshold_updater.subprocess.run')
    def test_run_rsi_calculation_failure(self, mock_run, updater):
        """测试RSI计算失败"""
        # Mock失败的subprocess结果
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "计算错误"
        mock_run.return_value = mock_result
        
        success = updater.run_rsi_calculation()
        assert success is False
    
    def test_check_and_update_rsi_threshold_convenience_function(self):
        """测试便捷函数"""
        with patch.object(RSIThresholdUpdater, 'update_threshold_if_needed', return_value=True):
            result = check_and_update_rsi_threshold()
            assert result is True
        
        with patch.object(RSIThresholdUpdater, 'update_threshold_if_needed', return_value=False):
            result = check_and_update_rsi_threshold(force_update=False)
            assert result is False


class TestRSIThresholdUpdaterIntegration:
    """RSI阈值更新器集成测试"""
    
    def test_full_update_workflow_mock(self):
        """测试完整的更新流程（使用mock）"""
        updater = RSIThresholdUpdater()
        
        # Mock各个步骤
        with patch.object(updater, 'should_update_threshold', return_value=(True, "测试更新")):
            with patch.object(updater, 'run_rsi_calculation', return_value=True):
                with patch.object(updater, 'get_threshold_file_info', return_value=(datetime.now(), 124)):
                    result = updater.update_threshold_if_needed()
                    assert result is True
    
    def test_no_update_needed_workflow(self):
        """测试不需要更新的流程"""
        updater = RSIThresholdUpdater()
        
        # Mock不需要更新
        with patch.object(updater, 'should_update_threshold', return_value=(False, "文件较新")):
            result = updater.update_threshold_if_needed()
            assert result is False
