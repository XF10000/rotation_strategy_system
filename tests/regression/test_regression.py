"""
回归测试 - 确保重构后结果一致

这些测试验证系统在重构或修改后，核心功能和结果保持一致。
"""

import json
import pytest
from pathlib import Path

from services.backtest_orchestrator import BacktestOrchestrator


class TestBacktestRegression:
    """回测结果回归测试"""
    
    @pytest.fixture
    def baseline(self):
        """加载基准数据"""
        baseline_file = Path(__file__).parent / 'baseline_v1.json'
        
        if not baseline_file.exists():
            pytest.skip("基准文件不存在，请先运行 create_baseline.py")
        
        with open(baseline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @pytest.fixture
    def current_results(self):
        """运行当前回测"""
        from config.csv_config_loader import load_backtest_settings, load_portfolio_config
        
        config_file = 'Input/Backtest_settings_regression_test.csv'
        portfolio_file = 'Input/portfolio_config.csv'
        
        # 加载配置
        config = load_backtest_settings(config_file)
        initial_holdings = load_portfolio_config(portfolio_file)
        config['initial_holdings'] = initial_holdings
        config['portfolio_config'] = portfolio_file
        
        orchestrator = BacktestOrchestrator(config)
        
        # 初始化
        assert orchestrator.initialize(), "协调器初始化失败"
        
        # 运行回测
        success = orchestrator.run_backtest()
        assert success, "回测运行失败"
        
        # 获取结果
        results = orchestrator.get_results()
        assert results is not None, "无法获取回测结果"
        
        return results
    
    def test_total_return_consistency(self, baseline, current_results):
        """测试总收益率一致性"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        current_return = performance.get('total_return', 0.0)
        baseline_return = baseline['total_return']
        
        # 允许0.01%的误差（由于浮点运算）
        tolerance = 0.0001
        assert abs(current_return - baseline_return) < tolerance, \
            f"总收益率不一致: 当前={current_return:.4%}, 基准={baseline_return:.4%}"
    
    def test_annual_return_consistency(self, baseline, current_results):
        """测试年化收益率一致性"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        current_annual = performance.get('annual_return', 0.0)
        baseline_annual = baseline['annual_return']
        
        tolerance = 0.0001
        assert abs(current_annual - baseline_annual) < tolerance, \
            f"年化收益率不一致: 当前={current_annual:.4%}, 基准={baseline_annual:.4%}"
    
    def test_max_drawdown_consistency(self, baseline, current_results):
        """测试最大回撤一致性"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        current_dd = performance.get('max_drawdown', 0.0)
        baseline_dd = baseline['max_drawdown']
        
        tolerance = 0.0001
        assert abs(current_dd - baseline_dd) < tolerance, \
            f"最大回撤不一致: 当前={current_dd:.4%}, 基准={baseline_dd:.4%}"
    
    def test_sharpe_ratio_consistency(self, baseline, current_results):
        """测试夏普比率一致性"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        current_sharpe = performance.get('sharpe_ratio', 0.0)
        baseline_sharpe = baseline['sharpe_ratio']
        
        tolerance = 0.001
        assert abs(current_sharpe - baseline_sharpe) < tolerance, \
            f"夏普比率不一致: 当前={current_sharpe:.3f}, 基准={baseline_sharpe:.3f}"
    
    def test_trade_count_consistency(self, baseline, current_results):
        """测试交易次数一致性"""
        current_count = len(current_results.get('transaction_history', []))
        baseline_count = baseline['trade_count']
        
        assert current_count == baseline_count, \
            f"交易次数不一致: 当前={current_count}, 基准={baseline_count}"
    
    def test_final_value_consistency(self, baseline, current_results):
        """测试最终资金一致性"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        current_value = performance.get('final_value', 0.0)
        baseline_value = baseline['final_value']
        
        # 允许1元的误差
        tolerance = 1.0
        assert abs(current_value - baseline_value) < tolerance, \
            f"最终资金不一致: 当前=¥{current_value:,.2f}, 基准=¥{baseline_value:,.2f}"
    
    def test_signal_count_consistency(self, baseline, current_results):
        """测试信号数量一致性"""
        backtest_results = current_results.get('backtest_results', {})
        signal_stats = backtest_results.get('signal_statistics', {})
        current_signals = signal_stats.get('total_signals', 0)
        baseline_signals = baseline['signal_count']
        
        assert current_signals == baseline_signals, \
            f"信号总数不一致: 当前={current_signals}, 基准={baseline_signals}"
    
    def test_all_metrics_summary(self, baseline, current_results):
        """测试所有指标汇总（用于调试）"""
        backtest_results = current_results.get('backtest_results', {})
        performance = backtest_results.get('performance_metrics', {})
        signal_stats = backtest_results.get('signal_statistics', {})
        
        print("\n" + "=" * 80)
        print("回归测试结果对比")
        print("=" * 80)
        
        metrics = [
            ('总收益率', baseline['total_return'], performance.get('total_return', 0.0), '%.4f%%'),
            ('年化收益率', baseline['annual_return'], performance.get('annual_return', 0.0), '%.4f%%'),
            ('最大回撤', baseline['max_drawdown'], performance.get('max_drawdown', 0.0), '%.4f%%'),
            ('夏普比率', baseline['sharpe_ratio'], performance.get('sharpe_ratio', 0.0), '%.3f'),
            ('索提诺比率', baseline['sortino_ratio'], performance.get('sortino_ratio', 0.0), '%.3f'),
            ('交易次数', baseline['trade_count'], len(current_results.get('transaction_history', [])), '%d'),
            ('最终资金', baseline['final_value'], performance.get('final_value', 0.0), '¥%.2f'),
            ('信号总数', baseline['signal_count'], signal_stats.get('total_signals', 0), '%d'),
        ]
        
        all_match = True
        for name, baseline_val, current_val, fmt in metrics:
            match = "✅" if abs(baseline_val - current_val) < 0.01 else "❌"
            if match == "❌":
                all_match = False
            
            baseline_str = fmt % (baseline_val * 100 if '%' in fmt and fmt != '%d' else baseline_val)
            current_str = fmt % (current_val * 100 if '%' in fmt and fmt != '%d' else current_val)
            
            print(f"{match} {name:12s}: 基准={baseline_str:>15s}  当前={current_str:>15s}")
        
        print("=" * 80)
        
        assert all_match, "部分指标不一致，请查看上方详情"
