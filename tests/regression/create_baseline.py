#!/usr/bin/env python3
"""
创建回归测试基准

运行完整回测并保存关键指标作为基准，用于后续回归测试。
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.backtest_orchestrator import BacktestOrchestrator
from config.csv_config_loader import load_backtest_settings, load_portfolio_config


def create_baseline():
    """创建回归测试基准"""
    
    print("=" * 80)
    print("创建回归测试基准")
    print("=" * 80)
    
    # 加载配置
    config_file = 'Input/Backtest_settings_regression_test.csv'
    portfolio_file = 'Input/portfolio_config.csv'
    
    print(f"\n📋 配置文件: {config_file}")
    print(f"📊 投资组合配置: {portfolio_file}")
    
    try:
        # 加载回测设置
        config = load_backtest_settings(config_file)
        
        # 加载投资组合配置
        initial_holdings = load_portfolio_config(portfolio_file)
        config['initial_holdings'] = initial_holdings
        config['portfolio_config'] = portfolio_file
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False
    
    # 运行回测
    print("\n🚀 开始运行回测...")
    orchestrator = BacktestOrchestrator(config)
    
    # 初始化协调器
    if not orchestrator.initialize():
        print("❌ 协调器初始化失败")
        return False
    
    success = orchestrator.run_backtest()
    
    if not success:
        print("❌ 回测失败")
        return False
    
    # 获取回测结果
    results = orchestrator.get_results()
    
    if not results:
        print("❌ 无法获取回测结果")
        return False
    
    # 提取关键指标（从backtest_results中获取）
    backtest_results = results.get('backtest_results', {})
    performance = backtest_results.get('performance_metrics', {})
    
    print(f"\n📊 性能指标: {performance}")
    
    baseline = {
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'config_file': config_file,
        
        # 收益指标
        'total_return': performance.get('total_return', 0.0),
        'annual_return': performance.get('annual_return', 0.0),
        'max_drawdown': performance.get('max_drawdown', 0.0),
        'sharpe_ratio': performance.get('sharpe_ratio', 0.0),
        'sortino_ratio': performance.get('sortino_ratio', 0.0),
        
        # 交易指标
        'trade_count': len(results.get('transaction_history', [])),
        'final_value': performance.get('final_value', 0.0),
        
        # 信号统计
        'signal_count': results.get('signal_statistics', {}).get('total_signals', 0),
        'buy_signals': results.get('signal_statistics', {}).get('buy_signals', 0),
        'sell_signals': results.get('signal_statistics', {}).get('sell_signals', 0),
    }
    
    # 保存基准
    baseline_file = project_root / 'tests' / 'regression' / 'baseline_v1.json'
    with open(baseline_file, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 基准已保存: {baseline_file}")
    print("\n📊 基准指标:")
    print(f"   总收益率: {baseline['total_return']:.2%}")
    print(f"   年化收益率: {baseline['annual_return']:.2%}")
    print(f"   最大回撤: {baseline['max_drawdown']:.2%}")
    print(f"   夏普比率: {baseline['sharpe_ratio']:.3f}")
    print(f"   索提诺比率: {baseline['sortino_ratio']:.3f}")
    print(f"   交易次数: {baseline['trade_count']}")
    print(f"   最终资金: ¥{baseline['final_value']:,.2f}")
    print(f"   信号总数: {baseline['signal_count']}")
    
    return True


if __name__ == '__main__':
    success = create_baseline()
    sys.exit(0 if success else 1)
