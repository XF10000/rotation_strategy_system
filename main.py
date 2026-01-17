"""
中线轮动策略系统 - 主程序入口
"""

import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import LOGGING_CONFIG, OUTPUT_CONFIG


def setup_logging():
    """设置日志系统"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, str(LOGGING_CONFIG['level'])),
        format=str(LOGGING_CONFIG['format']),
        handlers=[
            logging.FileHandler(str(LOGGING_CONFIG['file_path']), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """主程序入口"""
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("中线轮动策略系统启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 跳过旧的股票池验证，因为现在使用CSV配置
        logger.info("使用CSV配置，跳过传统股票池验证...")
        
        # 创建输出目录
        os.makedirs(OUTPUT_CONFIG['output_dir'], exist_ok=True)
        os.makedirs('data_cache', exist_ok=True)
        
        logger.info("系统初始化完成")
        
        # 导入回测相关模块
        from services.backtest_orchestrator import BacktestOrchestrator
        from backtest.performance_analyzer import PerformanceAnalyzer
        from config.csv_config_loader import create_csv_config
        from data.cache_validator import validate_cache_before_backtest

        # 直接使用CSV配置运行回测
        logger.info("使用CSV配置文件进行回测...")
        
        config = create_csv_config()
        logger.info(f"配置详情: {config['name']} - {config['description']}")
        logger.info(f"回测期间: {config['start_date']} 至 {config['end_date']}")
        logger.info(f"总资金: {config['total_capital']:,} 元")
        
        # 季度自动更新行业映射文件
        logger.info("📅 检查行业映射文件更新...")
        from utils.industry_mapping_updater import check_and_update_industry_mapping
        mapping_updated = check_and_update_industry_mapping()
        if mapping_updated:
            logger.info("✅ 行业映射文件已更新")
        
        # 季度自动更新RSI动态阈值文件
        logger.info("📊 检查RSI阈值文件更新...")
        from utils.rsi_threshold_updater import check_and_update_rsi_threshold
        rsi_updated = check_and_update_rsi_threshold()
        if rsi_updated:
            logger.info("✅ RSI阈值文件已更新")
        
        # 自动缓存验证和修复
        logger.info("🔍 执行缓存数据验证...")
        stock_codes = [code for code in config['initial_holdings'].keys() if code != 'cash']
        cache_validation_passed = validate_cache_before_backtest(stock_codes, 'weekly')
        
        if not cache_validation_passed:
            logger.error("❌ 缓存验证失败，回测终止")
            logger.error("💡 建议手动删除 data_cache/ 目录后重新运行回测")
            return
        
        # ✅ 使用BacktestOrchestrator（新架构）
        logger.info("🚀 初始化回测协调器...")
        orchestrator = BacktestOrchestrator(config)
        
        logger.info("📊 初始化服务层...")
        if not orchestrator.initialize():
            logger.error("❌ 初始化失败")
            return
        
        logger.info("▶️ 开始运行回测...")
        success = orchestrator.run_backtest()
        
        if not success:
            logger.error("❌ 回测运行失败")
            return
        
        logger.info("✅ 回测运行完成，开始生成报告...")
        
        # 生成完整报告（包含HTML、CSV等）
        report_files = orchestrator.generate_reports()
        
        # 获取回测结果用于性能分析
        portfolio_manager = orchestrator.portfolio_service.portfolio_manager
        
        # 创建绩效分析器并转换数据格式
        analyzer = PerformanceAnalyzer()
        
        # 将portfolio_history和transaction_history转换为DataFrame
        import pandas as pd
        if isinstance(portfolio_manager.portfolio_history, list):
            portfolio_df = pd.DataFrame(portfolio_manager.portfolio_history)
        else:
            portfolio_df = portfolio_manager.portfolio_history
        
        if isinstance(portfolio_manager.transaction_history, list):
            transaction_df = pd.DataFrame(portfolio_manager.transaction_history)
        else:
            transaction_df = portfolio_manager.transaction_history
        
        performance_report = analyzer.generate_performance_report(
            portfolio_df,
            transaction_df
        )
        
        # 打印绩效摘要
        logger.info("📈 回测结果摘要:")
        analyzer.print_performance_summary(performance_report)
        
        if report_files:
            logger.info("📄 报告生成完成:")
            for file_type, path in report_files.items():
                if file_type == 'html_report':
                    logger.info(f"  📊 HTML报告: {path}")
                elif file_type == 'csv_report':
                    logger.info(f"  📋 详细CSV报告: {path}")
                else:
                    logger.info(f"  📁 {file_type}: {path}")
        else:
            logger.warning("⚠️ 报告生成失败")
        
        logger.info("程序执行完成")
        logger.info("=" * 50)
        logger.info("=" * 50)
        logger.info("增强功能包括:")
        logger.info("✅ 详细交易记录 - 包含每次交易的技术指标数值")
        logger.info("✅ 4维信号状态分析 - 价值比过滤器+超买超卖+动能确认+极端价格量能")
        logger.info("✅ 信号触发原因 - 显示交易触发的具体原因和维度满足情况")
        logger.info("✅ 信号统计分析 - 各维度触发频率和满足度分布")
        logger.info("✅ 周K线图标注 - 在图表上标注交易位置")
        logger.info("✅ 技术指标面板 - RSI、MACD、成交量等多指标显示")
        logger.info("")
        logger.info("💡 提示: 打开生成的HTML报告查看完整的信号分析和K线图")
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()