#!/usr/bin/env python3
"""
缓存深度修复工具

当自动缓存验证失败时，使用此工具进行深度修复
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.cache_validator import CacheValidator
from config.csv_config_loader import load_backtest_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🔧 缓存深度修复工具")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        logger.info("📖 加载回测配置...")
        config = load_backtest_config()
        
        # 获取股票列表
        stock_codes = [code for code in config['initial_holdings'].keys() if code != 'cash']
        logger.info(f"📊 待检查股票数量: {len(stock_codes)}")
        logger.info(f"📋 股票列表: {', '.join(stock_codes)}")
        
        # 执行深度验证和修复
        logger.info("\n🔍 开始深度验证和修复...")
        validator = CacheValidator()
        
        # 对每只股票进行详细检查
        for i, stock_code in enumerate(stock_codes, 1):
            logger.info(f"\n[{i}/{len(stock_codes)}] 检查 {stock_code}...")
            validator.validate_and_fix([stock_code], 'weekly')
        
        # 获取最终状态
        status = validator.get_cache_health_status()
        
        logger.info("\n" + "=" * 60)
        if status == "HEALTHY":
            logger.info("✅ 所有缓存状态良好")
        elif status == "AUTO_FIXED":
            logger.info("✅ 缓存问题已全部修复")
        else:
            logger.error("❌ 仍存在无法自动修复的问题")
            logger.error("💡 建议手动删除 data_cache/ 目录后重新运行回测")
            return 1
        
        logger.info("=" * 60)
        logger.info("🎉 修复完成！现在可以运行 python3 main.py 进行回测")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 修复过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
