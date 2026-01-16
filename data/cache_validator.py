"""
缓存数据验证和自动修复模块
集成到主回测流程中，提供自动检测和修复功能
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

class CacheValidator:
    """缓存数据验证器 - 自动检测和修复数据问题"""
    
    def __init__(self, cache_dir: str = 'data_cache'):
        """初始化缓存验证器"""
        self.cache_dir = Path(cache_dir)
        self.stock_data_dir = self.cache_dir / 'stock_data'
        self.indicators_dir = self.cache_dir / 'indicators'
        
        # 验证结果
        self.validation_results = {
            'passed': True,
            'issues': [],
            'auto_fixed': [],
            'manual_action_required': []
        }
    
    def validate_and_fix(self, stock_codes: List[str], period: str = 'weekly') -> Dict[str, Any]:
        """
        验证缓存数据并自动修复问题
        
        Args:
            stock_codes: 需要验证的股票代码列表
            period: 数据周期
            
        Returns:
            Dict: 验证和修复结果
        """
        logger.info("🔍 开始缓存数据验证和自动修复...")
        
        # 重置验证结果
        self.validation_results = {
            'passed': True,
            'issues': [],
            'auto_fixed': [],
            'manual_action_required': []
        }
        
        try:
            # 1. 检查目录结构
            self._check_directory_structure()
            
            # 2. 验证股票数据完整性
            self._validate_stock_data(stock_codes, period)
            
            # 3. 验证技术指标数据
            self._validate_indicators_data(stock_codes)
            
            # 4. 检查数据格式一致性
            self._validate_data_format(stock_codes, period)
            
            # 5. 检查数据时间范围
            self._validate_date_ranges(stock_codes, period)
            
            # 6. 生成验证报告
            return self._generate_validation_report()
            
        except Exception as e:
            logger.error(f"❌ 缓存验证过程中出现错误: {e}")
            self.validation_results['passed'] = False
            self.validation_results['issues'].append(f"验证过程异常: {str(e)}")
            return self.validation_results
    
    def _check_directory_structure(self):
        """检查并修复目录结构"""
        required_dirs = [
            self.cache_dir,
            self.stock_data_dir,
            self.stock_data_dir / 'daily',
            self.stock_data_dir / 'weekly',
            self.stock_data_dir / 'monthly',
            self.indicators_dir
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                logger.info(f"🔧 创建缺失目录: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
                self.validation_results['auto_fixed'].append(f"创建目录: {dir_path}")
    
    def _validate_stock_data(self, stock_codes: List[str], period: str):
        """验证股票数据完整性"""
        logger.info(f"📊 验证 {len(stock_codes)} 只股票的 {period} 数据...")
        
        for code in stock_codes:
            try:
                # 检查数据文件是否存在
                data_file = self.stock_data_dir / period / f"{code}.csv"
                metadata_file = self.stock_data_dir / period / f"{code}.json"
                
                if not data_file.exists():
                    issue = f"股票数据文件缺失: {code} ({period})"
                    self.validation_results['issues'].append(issue)
                    self.validation_results['passed'] = False
                    continue
                
                # 检查数据是否可读
                try:
                    data = pd.read_csv(data_file, index_col=0, parse_dates=True)
                    
                    # 检查必要列是否存在
                    required_columns = ['open', 'high', 'low', 'close', 'volume']
                    missing_columns = [col for col in required_columns if col not in data.columns]
                    
                    if missing_columns:
                        issue = f"股票数据列缺失: {code} - {missing_columns}"
                        self.validation_results['issues'].append(issue)
                        self.validation_results['passed'] = False
                        
                        # 尝试自动修复：删除损坏的缓存文件
                        self._remove_corrupted_cache(code, period)
                        continue
                    
                    # 检查数据是否为空
                    if data.empty:
                        issue = f"股票数据为空: {code}"
                        self.validation_results['issues'].append(issue)
                        self.validation_results['passed'] = False
                        self._remove_corrupted_cache(code, period)
                        continue
                    
                    # 检查数据质量
                    self._validate_data_quality(data, code)
                    
                except Exception as e:
                    issue = f"股票数据读取失败: {code} - {str(e)}"
                    self.validation_results['issues'].append(issue)
                    self.validation_results['passed'] = False
                    self._remove_corrupted_cache(code, period)
                
            except Exception as e:
                logger.error(f"验证股票数据时出错 {code}: {e}")
    
    def _validate_indicators_data(self, stock_codes: List[str]):
        """验证技术指标数据"""
        logger.info("📈 验证技术指标数据...")
        
        for code in stock_codes:
            try:
                indicators_file = self.indicators_dir / f"{code}_indicators.csv"
                
                if indicators_file.exists():
                    try:
                        indicators = pd.read_csv(indicators_file, index_col=0, parse_dates=True)
                        
                        # 检查关键技术指标列
                        expected_indicators = ['ema_20w', 'ema_60w', 'rsi_14w', 'macd_dif', 'macd_dea', 'macd_hist']
                        missing_indicators = [ind for ind in expected_indicators if ind not in indicators.columns]
                        
                        if missing_indicators:
                            issue = f"技术指标缺失: {code} - {missing_indicators}"
                            self.validation_results['issues'].append(issue)
                            self.validation_results['passed'] = False
                            
                            # 删除不完整的指标缓存
                            indicators_file.unlink()
                            self.validation_results['auto_fixed'].append(f"删除不完整指标缓存: {code}")
                        
                    except Exception as e:
                        issue = f"技术指标数据损坏: {code} - {str(e)}"
                        self.validation_results['issues'].append(issue)
                        self.validation_results['passed'] = False
                        
                        # 删除损坏的指标缓存
                        if indicators_file.exists():
                            indicators_file.unlink()
                            self.validation_results['auto_fixed'].append(f"删除损坏指标缓存: {code}")
                
            except Exception as e:
                logger.error(f"验证技术指标时出错 {code}: {e}")
    
    def _validate_data_format(self, stock_codes: List[str], period: str):
        """验证数据格式一致性"""
        logger.info("🔍 验证数据格式一致性...")
        
        # 检查列名格式是否统一
        column_formats = {}
        
        for code in stock_codes:
            try:
                data_file = self.stock_data_dir / period / f"{code}.csv"
                if data_file.exists():
                    data = pd.read_csv(data_file, index_col=0, parse_dates=True, nrows=1)
                    columns_key = tuple(sorted(data.columns))
                    
                    if columns_key not in column_formats:
                        column_formats[columns_key] = []
                    column_formats[columns_key].append(code)
            
            except Exception as e:
                logger.warning(f"检查数据格式时出错 {code}: {e}")
        
        # 如果存在多种列格式，标记为问题
        if len(column_formats) > 1:
            issue = "数据格式不一致，存在多种列名格式"
            self.validation_results['issues'].append(issue)
            self.validation_results['passed'] = False
            
            # 找出最常见的格式作为标准
            standard_format = max(column_formats.keys(), key=lambda k: len(column_formats[k]))
            
            for columns, codes in column_formats.items():
                if columns != standard_format:
                    for code in codes:
                        self._remove_corrupted_cache(code, period)
                        self.validation_results['auto_fixed'].append(f"删除格式不一致的缓存: {code}")
    
    def _validate_date_ranges(self, stock_codes: List[str], period: str):
        """验证数据时间范围"""
        logger.info("📅 验证数据时间范围...")
        
        current_date = datetime.now()
        
        for code in stock_codes:
            try:
                metadata_file = self.stock_data_dir / period / f"{code}.json"
                
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # 检查数据是否过期（超过7天未更新）
                    save_time = datetime.fromisoformat(metadata['save_time'])
                    age_days = (current_date - save_time).days
                    
                    if age_days > 7:
                        issue = f"数据过期: {code} (已 {age_days} 天未更新)"
                        self.validation_results['issues'].append(issue)
                        # 注意：不自动删除过期数据，因为可能是周末或节假日
                        self.validation_results['manual_action_required'].append(f"检查数据源: {code}")
            
            except Exception as e:
                logger.warning(f"检查数据时间范围时出错 {code}: {e}")
    
    def _validate_data_quality(self, data: pd.DataFrame, code: str):
        """验证数据质量"""
        # 检查是否有异常值
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in numeric_columns:
            if col in data.columns:
                # 检查是否有NaN值
                if data[col].isna().any():
                    issue = f"数据包含NaN值: {code} - {col}列"
                    self.validation_results['issues'].append(issue)
                    self.validation_results['passed'] = False
                
                # 检查是否有负值（除了技术指标）
                if col != 'volume' and (data[col] < 0).any():
                    issue = f"数据包含负值: {code} - {col}列"
                    self.validation_results['issues'].append(issue)
                    self.validation_results['passed'] = False
                
                # 检查价格逻辑（high >= low, close在high和low之间）
                if col == 'high' and 'low' in data.columns:
                    if (data['high'] < data['low']).any():
                        issue = f"价格逻辑错误: {code} - 最高价低于最低价"
                        self.validation_results['issues'].append(issue)
                        self.validation_results['passed'] = False
    
    def _remove_corrupted_cache(self, code: str, period: str):
        """删除损坏的缓存文件"""
        try:
            data_file = self.stock_data_dir / period / f"{code}.csv"
            metadata_file = self.stock_data_dir / period / f"{code}.json"
            indicators_file = self.indicators_dir / f"{code}_indicators.csv"
            
            files_removed = []
            for file_path in [data_file, metadata_file, indicators_file]:
                if file_path.exists():
                    file_path.unlink()
                    files_removed.append(str(file_path))
            
            if files_removed:
                self.validation_results['auto_fixed'].append(f"删除损坏缓存: {code} - {len(files_removed)}个文件")
                logger.info(f"🗑️ 删除损坏的缓存文件: {code}")
        
        except Exception as e:
            logger.error(f"删除损坏缓存时出错 {code}: {e}")
    
    def _generate_validation_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        report = self.validation_results.copy()
        
        # 添加统计信息
        report['summary'] = {
            'total_issues': len(report['issues']),
            'auto_fixed_count': len(report['auto_fixed']),
            'manual_action_count': len(report['manual_action_required']),
            'validation_time': datetime.now().isoformat()
        }
        
        # 记录日志
        if report['passed']:
            logger.info("✅ 缓存数据验证通过")
        else:
            logger.warning(f"⚠️ 发现 {report['summary']['total_issues']} 个问题")
            logger.info(f"🔧 自动修复 {report['summary']['auto_fixed_count']} 个问题")
            
            if report['summary']['manual_action_count'] > 0:
                logger.warning(f"⚡ 需要手动处理 {report['summary']['manual_action_count']} 个问题")
        
        return report
    
    def get_cache_health_status(self) -> str:
        """获取缓存健康状态"""
        if self.validation_results['passed']:
            return "HEALTHY"
        elif len(self.validation_results['manual_action_required']) == 0:
            return "AUTO_FIXED"
        else:
            return "NEEDS_ATTENTION"


def validate_cache_before_backtest(stock_codes: List[str], period: str = 'weekly') -> bool:
    """
    回测前的缓存验证入口函数
    
    Args:
        stock_codes: 股票代码列表
        period: 数据周期
        
    Returns:
        bool: 是否可以继续回测
    """
    logger.info("🔍 执行回测前缓存验证...")
    
    validator = CacheValidator()
    result = validator.validate_and_fix(stock_codes, period)
    
    status = validator.get_cache_health_status()
    
    if status == "HEALTHY":
        logger.info("✅ 缓存状态良好，可以继续回测")
        return True
    elif status == "AUTO_FIXED":
        logger.info("🔧 缓存问题已自动修复，可以继续回测")
        return True
    else:
        logger.error("❌ 缓存存在需要手动处理的问题，建议检查后再回测")
        logger.error("💡 建议手动删除 data_cache/ 目录后重新运行回测")
        return False


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 测试验证功能
    test_codes = ['601088', '601225', '600985']
    result = validate_cache_before_backtest(test_codes)
    print(f"验证结果: {'通过' if result else '失败'}")
