#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业映射文件季度自动更新器
每个季度第一次运行时自动更新股票-行业映射文件
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
try:
    from .industry_mapper import IndustryMapper
except ImportError:
    from industry_mapper import IndustryMapper

logger = logging.getLogger(__name__)

class IndustryMappingUpdater:
    """行业映射文件季度自动更新器"""
    
    def __init__(self, mapping_file_path: str = "utils/stock_to_industry_map.json"):
        """
        初始化更新器
        
        Args:
            mapping_file_path: 映射文件路径
        """
        self.mapping_file_path = mapping_file_path
        self.quarters = {
            1: (1, 2, 3),    # Q1: 1-3月
            2: (4, 5, 6),    # Q2: 4-6月
            3: (7, 8, 9),    # Q3: 7-9月
            4: (10, 11, 12)  # Q4: 10-12月
        }
    
    def get_current_quarter(self, date: datetime = None) -> int:
        """
        获取当前季度
        
        Args:
            date: 指定日期，默认为当前日期
            
        Returns:
            int: 季度号 (1-4)
        """
        if date is None:
            date = datetime.now()
        
        month = date.month
        for quarter, months in self.quarters.items():
            if month in months:
                return quarter
        return 1  # 默认返回Q1
    
    def get_quarter_start_date(self, year: int, quarter: int) -> datetime:
        """
        获取指定季度的开始日期
        
        Args:
            year: 年份
            quarter: 季度号 (1-4)
            
        Returns:
            datetime: 季度开始日期
        """
        quarter_start_months = {1: 1, 2: 4, 3: 7, 4: 10}
        start_month = quarter_start_months[quarter]
        return datetime(year, start_month, 1)
    
    def get_mapping_file_info(self) -> Optional[Tuple[datetime, int]]:
        """
        获取映射文件的生成时间和股票数量
        
        Returns:
            Tuple[datetime, int]: (生成时间, 股票数量) 或 None
        """
        try:
            if not os.path.exists(self.mapping_file_path):
                logger.info(f"映射文件不存在: {self.mapping_file_path}")
                return None
            
            with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            generated_at_str = metadata.get('generated_at')
            total_stocks = metadata.get('total_stocks', 0)
            
            if not generated_at_str:
                logger.warning("映射文件缺少生成时间信息")
                return None
            
            # 解析生成时间
            generated_at = datetime.fromisoformat(generated_at_str.replace('Z', '+00:00'))
            if generated_at.tzinfo:
                generated_at = generated_at.replace(tzinfo=None)
            
            return generated_at, total_stocks
            
        except Exception as e:
            logger.error(f"读取映射文件信息失败: {e}")
            return None
    
    def should_update_mapping(self, force_update: bool = False) -> Tuple[bool, str]:
        """
        判断是否需要更新映射文件
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            Tuple[bool, str]: (是否需要更新, 原因说明)
        """
        if force_update:
            return True, "强制更新"
        
        # 获取映射文件信息
        file_info = self.get_mapping_file_info()
        if file_info is None:
            return True, "映射文件不存在或无效"
        
        generated_at, total_stocks = file_info
        now = datetime.now()
        
        # 获取当前季度和文件生成时的季度
        current_quarter = self.get_current_quarter(now)
        file_quarter = self.get_current_quarter(generated_at)
        
        # 检查是否跨季度
        if now.year > generated_at.year:
            return True, f"跨年度更新 ({generated_at.year} -> {now.year})"
        
        if current_quarter > file_quarter:
            return True, f"跨季度更新 (Q{file_quarter} -> Q{current_quarter})"
        
        # 检查文件是否过旧（超过4个月强制更新）
        age_days = (now - generated_at).days
        if age_days > 120:  # 4个月
            return True, f"文件过旧 ({age_days} 天)"
        
        # 检查股票数量是否异常少
        if total_stocks < 3000:
            return True, f"股票数量异常 ({total_stocks} < 3000)"
        
        return False, f"文件较新 (Q{current_quarter}, {age_days} 天前, {total_stocks} 只股票)"
    
    def update_mapping_if_needed(self, force_update: bool = False) -> bool:
        """
        根据需要更新映射文件
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            bool: 是否执行了更新
        """
        should_update, reason = self.should_update_mapping(force_update)
        
        logger.info(f"📅 映射文件更新检查: {reason}")
        
        if not should_update:
            logger.info("✅ 映射文件无需更新")
            return False
        
        logger.info(f"🔄 开始更新映射文件: {reason}")
        
        try:
            # 创建映射生成器并更新
            mapper = IndustryMapper(cache_dir="utils")
            mapping = mapper.run(force_refresh=True)
            
            logger.info(f"✅ 映射文件更新完成: {len(mapping)} 只股票")
            return True
            
        except Exception as e:
            logger.error(f"❌ 映射文件更新失败: {e}")
            return False
    
    def get_update_status(self) -> dict:
        """
        获取更新状态信息
        
        Returns:
            dict: 状态信息
        """
        file_info = self.get_mapping_file_info()
        now = datetime.now()
        
        if file_info is None:
            return {
                'file_exists': False,
                'generated_at': None,
                'total_stocks': 0,
                'age_days': None,
                'current_quarter': self.get_current_quarter(now),
                'file_quarter': None,
                'needs_update': True,
                'reason': '映射文件不存在'
            }
        
        generated_at, total_stocks = file_info
        age_days = (now - generated_at).days
        current_quarter = self.get_current_quarter(now)
        file_quarter = self.get_current_quarter(generated_at)
        needs_update, reason = self.should_update_mapping()
        
        return {
            'file_exists': True,
            'generated_at': generated_at.isoformat(),
            'total_stocks': total_stocks,
            'age_days': age_days,
            'current_quarter': current_quarter,
            'file_quarter': file_quarter,
            'needs_update': needs_update,
            'reason': reason
        }


def check_and_update_industry_mapping(force_update: bool = False) -> bool:
    """
    检查并更新行业映射文件的便捷函数
    
    Args:
        force_update: 是否强制更新
        
    Returns:
        bool: 是否执行了更新
    """
    updater = IndustryMappingUpdater()
    return updater.update_mapping_if_needed(force_update)


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='行业映射文件季度自动更新器')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制更新映射文件')
    parser.add_argument('--status', '-s', action='store_true',
                       help='显示映射文件状态')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    updater = IndustryMappingUpdater()
    
    if args.status:
        # 显示状态
        status = updater.get_update_status()
        print("📊 映射文件状态:")
        print("=" * 50)
        print(f"文件存在: {'✅' if status['file_exists'] else '❌'}")
        if status['file_exists']:
            print(f"生成时间: {status['generated_at']}")
            print(f"股票数量: {status['total_stocks']:,}")
            print(f"文件年龄: {status['age_days']} 天")
            print(f"当前季度: Q{status['current_quarter']}")
            print(f"文件季度: Q{status['file_quarter']}")
        print(f"需要更新: {'✅' if status['needs_update'] else '❌'}")
        print(f"更新原因: {status['reason']}")
    else:
        # 执行更新检查
        updated = updater.update_mapping_if_needed(args.force)
        if updated:
            print("✅ 映射文件已更新")
        else:
            print("ℹ️ 映射文件无需更新")
