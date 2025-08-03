"""
中线轮动策略系统 - 主程序入口
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import LOGGING_CONFIG, OUTPUT_CONFIG
from config.stock_pool import STOCK_POOL, validate_stock_pool

def setup_logging():
    """设置日志系统"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['level']),
        format=LOGGING_CONFIG['format'],
        handlers=[
            logging.FileHandler(LOGGING_CONFIG['file_path'], encoding='utf-8'),
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
        from backtest.backtest_engine import BacktestEngine
        from backtest.performance_analyzer import PerformanceAnalyzer
        from config.backtest_configs import get_config, list_configs
        
        # 直接使用CSV配置运行回测
        config_name = 'csv'
        logger.info(f"使用CSV配置文件进行回测...")
        
        config = get_config(config_name)
        logger.info(f"配置详情: {config['name']} - {config['description']}")
        logger.info(f"回测期间: {config['start_date']} 至 {config['end_date']}")
        logger.info(f"总资金: {config['total_capital']:,} 元")
        
        # 创建并运行回测引擎
        logger.info("初始化回测引擎...")
        engine = BacktestEngine(config)
        
        logger.info("开始运行回测...")
        success = engine.run_backtest()
        
        if not success:
            logger.error("回测运行失败")
            return
        
        # 获取回测结果
        backtest_results = engine.get_backtest_results()
        logger.info("回测运行完成，开始生成报告...")
        
        # 生成完整报告（包含HTML、CSV等）
        report_files = engine.generate_reports()
        
        # 创建绩效分析器
        analyzer = PerformanceAnalyzer()
        performance_report = analyzer.generate_performance_report(
            backtest_results['portfolio_history'],
            backtest_results['transaction_history']
        )
        
        # 打印绩效摘要
        logger.info("回测结果摘要:")
        analyzer.print_performance_summary(performance_report)
        
        if report_files:
            logger.info("报告生成完成:")
            for file_type, path in report_files.items():
                if file_type == 'html_report':
                    logger.info(f"  HTML报告: {path}")
                elif file_type == 'csv_report':
                    logger.info(f"  详细CSV报告: {path}")
                else:
                    logger.info(f"  {file_type}: {path}")
        else:
            logger.warning("报告生成失败")
        
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
        logger.info("💡 提示: 运行 'python3 run_signal_detailed_analysis.py' 查看更详细的信号分析")
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()