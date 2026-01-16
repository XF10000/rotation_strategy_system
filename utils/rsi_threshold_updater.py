#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RSI动态阈值文件季度自动更新器
每个季度第一次运行时自动更新申万二级行业RSI阈值文件
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

class RSIThresholdUpdater:
    """RSI动态阈值文件季度自动更新器"""
    
    def __init__(self, threshold_file_path: str = "sw_rsi_thresholds/output/sw2_rsi_threshold.csv"):
        """
        初始化更新器
        
        Args:
            threshold_file_path: RSI阈值文件路径
        """
        self.threshold_file_path = threshold_file_path
        self.calculation_script = "sw_rsi_thresholds/run_sw_2021_rsi_calculation.py"
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
    
    def get_threshold_file_info(self) -> Optional[Tuple[datetime, int]]:
        """
        获取RSI阈值文件的更新时间和行业数量
        
        Returns:
            Tuple[datetime, int]: (更新时间, 行业数量) 或 None
        """
        try:
            if not os.path.exists(self.threshold_file_path):
                logger.info(f"RSI阈值文件不存在: {self.threshold_file_path}")
                return None
            
            # 读取CSV文件
            df = pd.read_csv(self.threshold_file_path, encoding='utf-8')
            
            if df.empty:
                logger.warning("RSI阈值文件为空")
                return None
            
            # 获取更新时间（从更新时间列）
            if '更新时间' in df.columns and not df['更新时间'].empty:
                update_time_str = df['更新时间'].iloc[0]
                try:
                    # 解析更新时间 "2025-08-11 11:27:47"
                    update_time = datetime.strptime(update_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # 如果解析失败，使用文件修改时间
                    file_mtime = os.path.getmtime(self.threshold_file_path)
                    update_time = datetime.fromtimestamp(file_mtime)
            else:
                # 如果没有更新时间列，使用文件修改时间
                file_mtime = os.path.getmtime(self.threshold_file_path)
                update_time = datetime.fromtimestamp(file_mtime)
            
            # 获取行业数量
            industry_count = len(df)
            
            return update_time, industry_count
            
        except Exception as e:
            logger.error(f"读取RSI阈值文件信息失败: {e}")
            return None
    
    def should_update_threshold(self, force_update: bool = False) -> Tuple[bool, str]:
        """
        判断是否需要更新RSI阈值文件
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            Tuple[bool, str]: (是否需要更新, 原因说明)
        """
        if force_update:
            return True, "强制更新"
        
        # 获取阈值文件信息
        file_info = self.get_threshold_file_info()
        if file_info is None:
            return True, "RSI阈值文件不存在或无效"
        
        update_time, industry_count = file_info
        now = datetime.now()
        
        # 获取当前季度和文件更新时的季度
        current_quarter = self.get_current_quarter(now)
        file_quarter = self.get_current_quarter(update_time)
        
        # 检查是否跨季度
        if now.year > update_time.year:
            return True, f"跨年度更新 ({update_time.year} -> {now.year})"
        
        if current_quarter > file_quarter:
            return True, f"跨季度更新 (Q{file_quarter} -> Q{current_quarter})"
        
        # 检查文件是否过旧（超过4个月强制更新）
        age_days = (now - update_time).days
        if age_days > 120:  # 4个月
            return True, f"文件过旧 ({age_days} 天)"
        
        # 检查行业数量是否异常少
        if industry_count < 100:  # 申万二级行业应该有124个左右
            return True, f"行业数量异常 ({industry_count} < 100)"
        
        return False, f"文件较新 (Q{current_quarter}, {age_days} 天前, {industry_count} 个行业)"
    
    def run_rsi_calculation(self) -> bool:
        """
        运行RSI阈值计算脚本
        
        Returns:
            bool: 是否计算成功
        """
        try:
            logger.info("🔄 开始计算RSI动态阈值...")
            
            # 检查计算脚本是否存在
            if not os.path.exists(self.calculation_script):
                logger.error(f"RSI计算脚本不存在: {self.calculation_script}")
                return False
            
            # 运行计算脚本
            cmd = [sys.executable, self.calculation_script, "--output", "output"]
            
            # 切换到sw_rsi_thresholds目录
            script_dir = os.path.dirname(self.calculation_script)
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {script_dir}")
            
            result = subprocess.run(
                cmd,
                cwd=script_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                logger.info("✅ RSI阈值计算完成")
                logger.debug(f"输出: {result.stdout}")
                return True
            else:
                logger.error(f"❌ RSI阈值计算失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ RSI阈值计算超时")
            return False
        except Exception as e:
            logger.error(f"❌ RSI阈值计算异常: {e}")
            return False
    
    def update_threshold_if_needed(self, force_update: bool = False) -> bool:
        """
        根据需要更新RSI阈值文件
        
        Args:
            force_update: 是否强制更新
            
        Returns:
            bool: 是否执行了更新
        """
        should_update, reason = self.should_update_threshold(force_update)
        
        logger.info(f"📊 RSI阈值文件更新检查: {reason}")
        
        if not should_update:
            logger.info("✅ RSI阈值文件无需更新")
            return False
        
        logger.info(f"🔄 开始更新RSI阈值文件: {reason}")
        
        # 执行RSI阈值计算
        success = self.run_rsi_calculation()
        
        if success:
            # 验证生成的文件
            file_info = self.get_threshold_file_info()
            if file_info:
                update_time, industry_count = file_info
                logger.info(f"✅ RSI阈值文件更新完成: {industry_count} 个行业")
                return True
            else:
                logger.error("❌ RSI阈值文件更新后验证失败")
                return False
        else:
            logger.error("❌ RSI阈值文件更新失败")
            return False
    
    def get_update_status(self) -> dict:
        """
        获取更新状态信息
        
        Returns:
            dict: 状态信息
        """
        file_info = self.get_threshold_file_info()
        now = datetime.now()
        
        if file_info is None:
            return {
                'file_exists': False,
                'update_time': None,
                'industry_count': 0,
                'age_days': None,
                'current_quarter': self.get_current_quarter(now),
                'file_quarter': None,
                'needs_update': True,
                'reason': 'RSI阈值文件不存在'
            }
        
        update_time, industry_count = file_info
        age_days = (now - update_time).days
        current_quarter = self.get_current_quarter(now)
        file_quarter = self.get_current_quarter(update_time)
        needs_update, reason = self.should_update_threshold()
        
        return {
            'file_exists': True,
            'update_time': update_time.isoformat(),
            'industry_count': industry_count,
            'age_days': age_days,
            'current_quarter': current_quarter,
            'file_quarter': file_quarter,
            'needs_update': needs_update,
            'reason': reason
        }


def check_and_update_rsi_threshold(force_update: bool = False) -> bool:
    """
    检查并更新RSI阈值文件的便捷函数
    
    Args:
        force_update: 是否强制更新
        
    Returns:
        bool: 是否执行了更新
    """
    updater = RSIThresholdUpdater()
    return updater.update_threshold_if_needed(force_update)


if __name__ == "__main__":
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='RSI阈值文件季度自动更新器')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制更新RSI阈值文件')
    parser.add_argument('--status', '-s', action='store_true',
                       help='显示RSI阈值文件状态')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    updater = RSIThresholdUpdater()
    
    if args.status:
        # 显示状态
        status = updater.get_update_status()
        print("📊 RSI阈值文件状态:")
        print("=" * 50)
        print(f"文件存在: {'✅' if status['file_exists'] else '❌'}")
        if status['file_exists']:
            print(f"更新时间: {status['update_time']}")
            print(f"行业数量: {status['industry_count']:,}")
            print(f"文件年龄: {status['age_days']} 天")
            print(f"当前季度: Q{status['current_quarter']}")
            print(f"文件季度: Q{status['file_quarter']}")
        print(f"需要更新: {'✅' if status['needs_update'] else '❌'}")
        print(f"更新原因: {status['reason']}")
    else:
        # 执行更新检查
        updated = updater.update_threshold_if_needed(args.force)
        if updated:
            print("✅ RSI阈值文件已更新")
        else:
            print("ℹ️ RSI阈值文件无需更新")
