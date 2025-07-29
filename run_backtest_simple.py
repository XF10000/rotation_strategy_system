#!/usr/bin/env python3
"""
简化版回测运行脚本
禁用智能缓存，直接获取完整数据
"""

import sys
import logging
from datetime import datetime
import pandas as pd

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest_simple.log'),
        logging.StreamHandler()
    ]
)

def main():
    """简化版回测主函数"""
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("🚀 简化版回测系统启动")
    print("=" * 60)
    
    try:
        # 导入必要模块
        from config.csv_config_loader import create_csv_config
        from data.data_fetcher import AkshareDataFetcher
        from data.data_processor import DataProcessor
        from strategy.signal_generator import SignalGenerator
        from backtest.portfolio_manager import PortfolioManager
        from backtest.transaction_cost import TransactionCostCalculator
        
        # 1. 加载配置
        logger.info("📋 加载配置...")
        config = create_csv_config()
        
        logger.info(f"回测期间: {config['start_date']} 到 {config['end_date']}")
        stock_codes = [k for k in config['initial_holdings'].keys() if k != 'cash']
        logger.info(f"股票池: {stock_codes}")
        logger.info(f"总资金: {config['total_capital']:,} 元")
        
        # 2. 初始化组件
        logger.info("🔧 初始化组件...")
        data_fetcher = AkshareDataFetcher()
        data_processor = DataProcessor()
        signal_generator = SignalGenerator(config)
        portfolio_manager = PortfolioManager(config['total_capital'], config['initial_holdings'])
        cost_calculator = TransactionCostCalculator()
        
        # 3. 获取所有股票数据（不使用缓存）
        logger.info("📊 获取股票数据...")
        all_stock_data = {}
        failed_stocks = []
        
        for i, stock_code in enumerate(stock_codes, 1):
            logger.info(f"[{i}/{len(stock_codes)}] 获取 {stock_code} 数据...")
            
            try:
                # 直接获取完整期间的日线数据
                daily_data = data_fetcher.get_stock_data(
                    stock_code, 
                    config['start_date'], 
                    config['end_date'], 
                    'daily'
                )
                
                if daily_data is not None and not daily_data.empty:
                    # 转换为周线数据
                    weekly_data = data_processor.resample_to_weekly(daily_data)
                    
                    # 计算技术指标
                    weekly_data = data_processor.calculate_technical_indicators(weekly_data)
                    
                    all_stock_data[stock_code] = {
                        'daily': daily_data,
                        'weekly': weekly_data
                    }
                    
                    logger.info(f"✅ {stock_code} 数据获取成功: 日线{len(daily_data)}条, 周线{len(weekly_data)}条")
                else:
                    logger.warning(f"❌ {stock_code} 数据为空")
                    failed_stocks.append(stock_code)
                    
            except Exception as e:
                logger.error(f"❌ {stock_code} 数据获取失败: {e}")
                failed_stocks.append(stock_code)
            
            # 添加延迟避免请求过快
            import time
            time.sleep(1)
        
        # 4. 检查数据获取结果
        success_count = len(all_stock_data)
        total_count = len(stock_codes)
        
        logger.info(f"📈 数据获取完成: 成功{success_count}/{total_count}")
        
        if failed_stocks:
            logger.warning(f"失败的股票: {failed_stocks}")
        
        if success_count == 0:
            logger.error("❌ 没有成功获取任何股票数据，无法进行回测")
            return
        
        # 5. 初始化投资组合
        logger.info("💼 初始化投资组合...")
        
        # 获取初始价格（使用第一个有效交易日的价格）
        initial_prices = {}
        for stock_code in all_stock_data.keys():
            weekly_data = all_stock_data[stock_code]['weekly']
            if not weekly_data.empty:
                initial_prices[stock_code] = weekly_data['close'].iloc[0]
        
        # 初始化投资组合
        portfolio_manager.initialize_portfolio(initial_prices)
        
        # 6. 运行回测
        logger.info("🔄 开始回测...")
        
        # 获取所有交易日期
        all_dates = set()
        for data in all_stock_data.values():
            all_dates.update(data['weekly'].index)
        
        trading_dates = sorted(list(all_dates))
        logger.info(f"回测期间共 {len(trading_dates)} 个交易周")
        
        # 交易记录
        trading_records = []
        
        # 逐周回测
        for i, current_date in enumerate(trading_dates):
            if i % 50 == 0:
                logger.info(f"回测进度: {i}/{len(trading_dates)} ({i/len(trading_dates)*100:.1f}%)")
            
            # 为每只股票生成信号
            for stock_code in all_stock_data.keys():
                weekly_data = all_stock_data[stock_code]['weekly']
                
                if current_date not in weekly_data.index:
                    continue
                
                # 获取当前数据
                current_idx = weekly_data.index.get_loc(current_date)
                if current_idx < 60:  # 需要足够的历史数据
                    continue
                
                historical_data = weekly_data.iloc[:current_idx+1]
                
                # 生成信号
                try:
                    signal_result = signal_generator.generate_signal(
                        stock_code, 
                        historical_data
                    )
                    
                    if signal_result and signal_result.get('signal') in ['BUY', 'SELL']:
                        # 执行交易
                        signal_type = signal_result['signal']
                        current_price = historical_data['close'].iloc[-1]
                        
                        if signal_type == 'BUY':
                            # 计算买入数量（10%轮动）
                            rotation_ratio = config['strategy_params']['rotation_percentage']
                            
                            # 检查是否可以买入
                            can_buy, buy_shares, buy_value = portfolio_manager.can_buy(
                                stock_code, rotation_ratio, current_price
                            )
                            
                            if can_buy and buy_shares > 0:
                                transaction_cost = cost_calculator.calculate_buy_cost(buy_value)
                                
                                success = portfolio_manager.execute_buy(
                                    stock_code, buy_shares, current_price,
                                    transaction_cost, current_date,
                                    signal_result.get('reason', '买入信号')
                                )
                                
                                if success:
                                    # 记录交易
                                    trading_records.append({
                                        'date': current_date,
                                        'type': '买入',
                                        'stock_code': stock_code,
                                        'shares': buy_shares,
                                        'price': current_price,
                                        'amount': buy_value,
                                        'cost': transaction_cost,
                                        'reason': signal_result.get('reason', ''),
                                        'position_after': portfolio_manager.holdings.get(stock_code, 0)
                                    })
                        
                        elif signal_type == 'SELL':
                            # 卖出持仓的10%
                            rotation_ratio = config['strategy_params']['rotation_percentage']
                            
                            # 检查是否可以卖出
                            can_sell, sell_shares, sell_value = portfolio_manager.can_sell(
                                stock_code, rotation_ratio, current_price
                            )
                            
                            if can_sell and sell_shares > 0:
                                transaction_cost = cost_calculator.calculate_sell_cost(sell_value)
                                
                                success = portfolio_manager.execute_sell(
                                    stock_code, sell_shares, current_price,
                                    transaction_cost, current_date,
                                    signal_result.get('reason', '卖出信号')
                                )
                                
                                if success:
                                    # 记录交易
                                    trading_records.append({
                                        'date': current_date,
                                        'type': '卖出',
                                        'stock_code': stock_code,
                                        'shares': sell_shares,
                                        'price': current_price,
                                        'amount': sell_value,
                                        'cost': transaction_cost,
                                        'reason': signal_result.get('reason', ''),
                                        'position_after': portfolio_manager.holdings.get(stock_code, 0)
                                    })
                
                except Exception as e:
                    logger.debug(f"股票 {stock_code} 在 {current_date} 信号生成失败: {e}")
                    continue
        
        # 7. 生成报告
        logger.info("📊 生成回测报告...")
        
        # 计算最终收益
        final_prices = {}
        for stock_code in all_stock_data.keys():
            weekly_data = all_stock_data[stock_code]['weekly']
            if not weekly_data.empty:
                final_prices[stock_code] = weekly_data['close'].iloc[-1]
        
        final_value = portfolio_manager.get_total_value(final_prices)
        total_return = (final_value - config['total_capital']) / config['total_capital'] * 100
        
        logger.info(f"🎯 回测完成!")
        logger.info(f"初始资金: {config['total_capital']:,.0f} 元")
        logger.info(f"最终价值: {final_value:,.0f} 元")
        logger.info(f"总收益率: {total_return:.2f}%")
        logger.info(f"交易次数: {len(trading_records)}")
        
        # 导出交易记录
        if trading_records:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"reports/simple_backtest_records_{timestamp}.csv"
            
            df_records = pd.DataFrame(trading_records)
            df_records.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            logger.info(f"📄 交易记录已导出: {csv_filename}")
        
        print("\n" + "=" * 60)
        print("🎉 简化版回测完成!")
        print(f"📊 总收益率: {total_return:.2f}%")
        print(f"📈 交易次数: {len(trading_records)}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()