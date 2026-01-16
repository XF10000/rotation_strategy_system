"""
完整回测验证脚本
使用BacktestOrchestrator运行完整回测并生成报告
"""

import logging
import sys

from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator
from backtest.backtest_engine import BacktestEngine

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """运行完整回测"""
    print("=" * 80)
    print("完整回测验证 - BacktestOrchestrator")
    print("=" * 80)
    
    try:
        # 加载配置
        logger.info("加载配置文件...")
        backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
        initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
        config = {**backtest_settings}
        config['initial_holdings'] = initial_holdings
        
        logger.info(f"回测期间: {config['start_date']} 至 {config['end_date']}")
        logger.info(f"初始资金: ¥{config['total_capital']:,.0f}")
        logger.info(f"股票池: {len(initial_holdings)-1} 只股票")  # -1 排除现金
        
        # 🔧 修复：创建BacktestEngine用于K线数据准备
        logger.info("\n创建BacktestEngine（用于K线数据准备）...")
        backtest_engine = BacktestEngine(config)
        logger.info("BacktestEngine创建完成")
        
        # 🔧 修复：准备股票数据
        logger.info("准备股票数据...")
        backtest_engine.prepare_data()
        logger.info(f"股票数据准备完成，共 {len(backtest_engine.stock_data)} 只股票")
        
        # 创建并初始化Orchestrator
        logger.info("\n创建BacktestOrchestrator...")
        orchestrator = BacktestOrchestrator(config)
        
        # 🔧 修复：将backtest_engine传递给orchestrator
        orchestrator.backtest_engine = backtest_engine
        orchestrator.stock_data = backtest_engine.stock_data  # 共享股票数据
        
        logger.info("初始化服务层...")
        if not orchestrator.initialize():
            logger.error("初始化失败")
            return False
        
        # 运行回测
        logger.info("\n开始回测...")
        orchestrator.run_backtest()
        
        # 获取结果
        logger.info("\n回测完成，统计结果...")
        pm = orchestrator.portfolio_service.portfolio_manager
        
        # 获取最新价格（从最后一次更新）
        # 需要从stock_data中获取最后一个交易日的价格
        import pandas as pd
        end_date = pd.Timestamp(config['end_date'])
        current_prices = {}
        for code in orchestrator.stock_data.keys():
            weekly_data = orchestrator.stock_data[code]['weekly']
            if end_date in weekly_data.index:
                current_prices[code] = weekly_data.loc[end_date, 'close']
            else:
                # 使用最后可用的价格
                current_prices[code] = weekly_data['close'].iloc[-1]
        
        # 计算最终资金
        cash = pm.cash
        holdings_value = sum(
            pm.holdings.get(code, 0) * current_prices.get(code, 0)
            for code in pm.holdings.keys()
        )
        total_value = cash + holdings_value
        
        # 计算收益率
        initial_capital = config['total_capital']
        total_return = (total_value - initial_capital) / initial_capital * 100
        
        # 计算年化收益率
        import pandas as pd
        start_date = pd.Timestamp(config['start_date'])
        end_date = pd.Timestamp(config['end_date'])
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = ((1 + total_return/100) ** (1/years) - 1) * 100
        
        # 交易统计
        transactions = pm.transaction_history
        buy_count = sum(1 for t in transactions if t.get('type') == 'BUY')
        sell_count = sum(1 for t in transactions if t.get('type') == 'SELL')
        
        # 输出结果
        print("\n" + "=" * 80)
        print("回测结果摘要")
        print("=" * 80)
        print(f"\n📊 基本信息:")
        print(f"   回测期间: {config['start_date']} 至 {config['end_date']}")
        print(f"   回测天数: {days} 天 ({years:.2f} 年)")
        print(f"   股票池: {len(initial_holdings)-1} 只股票")
        
        print(f"\n💰 资金状况:")
        print(f"   初始资金: ¥{initial_capital:,.2f}")
        print(f"   现金余额: ¥{cash:,.2f}")
        print(f"   持仓价值: ¥{holdings_value:,.2f}")
        print(f"   最终资金: ¥{total_value:,.2f}")
        
        print(f"\n📈 收益指标:")
        print(f"   总收益: ¥{total_value - initial_capital:,.2f}")
        print(f"   总收益率: {total_return:.2f}%")
        print(f"   年化收益率: {annual_return:.2f}%")
        
        print(f"\n💼 交易统计:")
        print(f"   总交易次数: {len(transactions)} 笔")
        print(f"   买入次数: {buy_count} 笔")
        print(f"   卖出次数: {sell_count} 笔")
        
        print(f"\n📋 持仓明细:")
        print(f"   持仓股票数: {len([h for h in pm.holdings.values() if h > 0])} 只")
        for code, shares in sorted(pm.holdings.items()):
            if shares > 0:
                price = current_prices.get(code, 0)
                value = shares * price
                weight = value / total_value * 100 if total_value > 0 else 0
                print(f"   {code}: {shares:>10,.0f} 股 @ ¥{price:>8.2f} = ¥{value:>12,.2f} ({weight:>5.2f}%)")
        
        print("\n" + "=" * 80)
        print(f"\n💼 交易统计:")
        print(f"   总交易次数: {len(transactions)} 笔")
        print(f"   买入次数: {buy_count} 笔")
        print(f"   卖出次数: {sell_count} 笔")
        
        print("\n" + "=" * 80)
        
        # 生成HTML报告
        logger.info("\n生成HTML报告...")
        try:
            report_paths = orchestrator.generate_reports()
            if report_paths:
                print(f"\n📄 报告已生成:")
                for report_type, path in report_paths.items():
                    print(f"   {report_type}: {path}")
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return True
        
    except Exception as e:
        logger.error(f"回测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
