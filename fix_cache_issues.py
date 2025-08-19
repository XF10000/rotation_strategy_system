#!/usr/bin/env python3
"""
数据缓存问题修复工具 - 深度修复版本
解决2024年8月前技术指标缺失和列名不匹配问题

注意：从V2.0开始，main.py已集成自动缓存验证和修复功能。
本工具仅用于处理自动修复无法解决的复杂问题。
正常情况下，您不需要手动运行此工具。
"""

import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_cache_issues():
    """修复缓存数据问题"""
    
    logger.info("🚀 开始修复数据缓存问题...")
    
    # 1. 清理所有股票数据缓存，强制重新计算
    cache_dir = Path('data_cache')
    stock_data_dir = cache_dir / 'stock_data'
    
    if stock_data_dir.exists():
        logger.info("🗑️ 清理现有股票数据缓存...")
        
        # 清理日线和周线缓存
        for period in ['daily', 'weekly']:
            period_dir = stock_data_dir / period
            if period_dir.exists():
                # 删除所有CSV和JSON文件
                csv_files = list(period_dir.glob('*.csv'))
                json_files = list(period_dir.glob('*.json'))
                
                for file in csv_files + json_files:
                    file.unlink()
                    
                logger.info(f"   清理 {period} 目录: {len(csv_files)} CSV + {len(json_files)} JSON")
    
    # 2. 清理技术指标缓存
    indicators_dir = cache_dir / 'indicators'
    if indicators_dir.exists():
        indicator_files = list(indicators_dir.glob('*.csv'))
        for file in indicator_files:
            file.unlink()
        logger.info(f"🗑️ 清理技术指标缓存: {len(indicator_files)} 个文件")
    
    # 3. 清理信号缓存
    signals_dir = cache_dir / 'signals'
    if signals_dir.exists():
        import shutil
        shutil.rmtree(signals_dir)
        signals_dir.mkdir(exist_ok=True)
        logger.info("🗑️ 清理信号缓存目录")
    
    logger.info("✅ 缓存清理完成，系统将重新获取和计算所有数据")
    
    # 4. 验证行业映射文件
    industry_map_file = cache_dir / 'stock_to_industry_map.json'
    if industry_map_file.exists():
        try:
            with open(industry_map_file, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            
            mapping = map_data.get('mapping', {})
            logger.info(f"✅ 行业映射文件正常: {len(mapping)} 只股票")
            
            # 检查关键股票
            test_stocks = ['600985', '601225', '601088']
            for stock in test_stocks:
                if stock in mapping:
                    industry_info = mapping[stock]
                    logger.info(f"   {stock}: {industry_info.get('industry_name', '未知')}")
                else:
                    logger.warning(f"   {stock}: 映射缺失")
                    
        except Exception as e:
            logger.error(f"❌ 行业映射文件有问题: {e}")
            return False
    else:
        logger.error("❌ 行业映射文件不存在，需要重新生成")
        return False
    
    return True

def validate_technical_indicators():
    """验证技术指标计算是否正确"""
    
    logger.info("🔍 验证技术指标计算...")
    
    # 导入必要的模块
    import sys
    sys.path.append('.')
    
    from indicators.trend import calculate_ema
    from indicators.momentum import calculate_rsi, calculate_macd
    from indicators.volatility import calculate_bollinger_bands
    
    # 创建测试数据
    dates = pd.date_range('2020-01-01', '2025-08-01', freq='W')
    np.random.seed(42)  # 固定随机种子
    
    test_data = pd.DataFrame({
        'close': 10 + np.cumsum(np.random.randn(len(dates)) * 0.1),
        'high': 0,
        'low': 0,
        'volume': np.random.randint(100000, 1000000, len(dates))
    }, index=dates)
    
    # 调整high和low
    test_data['high'] = test_data['close'] * (1 + np.random.uniform(0, 0.05, len(dates)))
    test_data['low'] = test_data['close'] * (1 - np.random.uniform(0, 0.05, len(dates)))
    
    logger.info(f"📊 测试数据: {len(test_data)} 条记录")
    
    try:
        # 测试各项技术指标计算
        logger.info("   测试EMA计算...")
        ema_20 = calculate_ema(test_data['close'], 20)
        logger.info(f"   EMA20: {len(ema_20.dropna())} 个有效值")
        
        logger.info("   测试RSI计算...")
        rsi_14 = calculate_rsi(test_data['close'], 14)
        logger.info(f"   RSI14: {len(rsi_14.dropna())} 个有效值")
        
        logger.info("   测试MACD计算...")
        macd_result = calculate_macd(test_data['close'])
        logger.info(f"   MACD: DIF={len(macd_result['dif'].dropna())} 个有效值")
        
        logger.info("   测试布林带计算...")
        bb_result = calculate_bollinger_bands(test_data['close'], 20, 2)
        logger.info(f"   布林带: {len(bb_result['upper'].dropna())} 个有效值")
        
        logger.info("✅ 技术指标计算验证通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 技术指标计算验证失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🔧 数据缓存问题修复工具")
    logger.info("=" * 60)
    
    # 1. 修复缓存问题
    if not fix_cache_issues():
        logger.error("❌ 缓存修复失败")
        return 1
    
    # 2. 验证技术指标计算
    if not validate_technical_indicators():
        logger.error("❌ 技术指标验证失败")
        return 1
    
    logger.info("=" * 60)
    logger.info("✅ 修复完成！建议步骤：")
    logger.info("1. 运行 python3 main.py 重新进行回测")
    logger.info("2. 检查技术指标是否正确计算")
    logger.info("3. 验证交易信号是否正常生成")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
