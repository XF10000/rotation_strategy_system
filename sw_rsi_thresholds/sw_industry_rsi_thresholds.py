"""
申万二级行业RSI阈值计算模块
根据行业波动率分层，动态计算RSI超买超卖阈值
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import time
from typing import Dict, Tuple, List

# 导入配置文件
try:
    from .config import RSI_THRESHOLDS, CALCULATION_PERIODS, DATA_QUALITY, OUTPUT_CONFIG, EXTREME_THRESHOLD_COEFFICIENTS
except ImportError:
    # 如果作为脚本直接运行，使用相对导入
    from config import RSI_THRESHOLDS, CALCULATION_PERIODS, DATA_QUALITY, OUTPUT_CONFIG, EXTREME_THRESHOLD_COEFFICIENTS

try:
    import talib
    USE_TALIB = True
except ImportError:
    USE_TALIB = False
    print("Warning: talib not available, using custom RSI implementation")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    计算RSI指标
    
    Args:
        prices: 价格序列
        period: RSI周期
        
    Returns:
        RSI序列
    """
    if USE_TALIB:
        return pd.Series(talib.RSI(prices.values, timeperiod=period), index=prices.index)
    else:
        # 自定义RSI计算
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class SWIndustryRSIThresholds:
    """申万二级行业RSI阈值计算器"""
    
    def __init__(self, output_dir: str = "output"):
        """
        初始化
        
        Args:
            output_dir: 输出文件目录
        """
        self.output_dir = output_dir
        
        # 从配置文件读取参数
        self.rsi_period = CALCULATION_PERIODS["rsi_period"]
        self.lookback_weeks = CALCULATION_PERIODS["lookback_weeks"]
        self.retry_times = DATA_QUALITY["retry_times"]
        self.retry_delay = DATA_QUALITY["retry_delay"]
        self.min_data_points = DATA_QUALITY["min_data_points"]
        self.min_rsi_points = DATA_QUALITY["min_rsi_points"]
        
        # RSI阈值配置
        self.rsi_thresholds = RSI_THRESHOLDS
        self.volatility_quantiles = CALCULATION_PERIODS["volatility_quantiles"]
        self.extreme_threshold_coefficients = EXTREME_THRESHOLD_COEFFICIENTS
        
        # 输出配置
        self.output_config = OUTPUT_CONFIG
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 打印当前配置
        logger.info("RSI阈值计算配置:")
        logger.info(f"  历史数据周数: {self.lookback_weeks}")
        logger.info(f"  RSI计算周期: {self.rsi_period}")
        logger.info(f"  普通阈值: 超卖{self.rsi_thresholds['普通超卖']}%, 超买{self.rsi_thresholds['普通超买']}%")
        logger.info(f"  波动率分层: Q1={self.volatility_quantiles['q1']}%, Q3={self.volatility_quantiles['q3']}%")
    
    def get_sw_industry_codes(self) -> pd.DataFrame:
        """
        获取申万二级行业代码和名称
        
        Returns:
            包含行业代码和名称的DataFrame
        """
        try:
            logger.info("使用AkShare API获取申万二级行业分类...")
            
            # 使用AkShare的sw_index_second_info接口
            sw_industry = ak.sw_index_second_info()
            
            if sw_industry.empty:
                raise ValueError("AkShare API返回空数据")
            
            logger.debug(f"API返回数据列名: {list(sw_industry.columns)}")
            logger.debug(f"API返回数据样例:\n{sw_industry.head()}")
            
            # 处理返回的数据格式
            if '行业代码' in sw_industry.columns and '行业名称' in sw_industry.columns:
                # 提取需要的列
                df = sw_industry[['行业代码', '行业名称']].copy()
                
                # 处理行业代码格式（去掉可能的.SI后缀）
                df['行业代码'] = df['行业代码'].astype(str)
                df['行业代码'] = df['行业代码'].str.replace('.SI', '', regex=False)
                
                # 重命名列以保持一致性
                df = df.rename(columns={'行业代码': '指数代码', '行业名称': '指数名称'})
                
                # 去重并排序
                df = df.drop_duplicates().sort_values('指数代码').reset_index(drop=True)
                
                logger.info(f"通过AkShare API获取到 {len(df)} 个申万二级行业")
                logger.info(f"行业代码格式示例: {df['指数代码'].head(3).tolist()}")
                
                return df
            else:
                raise ValueError(f"API返回数据格式不符合预期，列名: {list(sw_industry.columns)}")
                
        except Exception as e:
            logger.error(f"AkShare API获取申万行业分类失败: {e}")
            # 备用方案：使用预定义列表
            logger.info("使用预定义的申万二级行业列表...")
            fallback_codes = {
                    '620100': '房屋建设', '480400': '城商行', '480500': '农商行', '480300': '股份制银行',
                    '480200': '国有大型银行', '490200': '保险', '421100': '航运港口', '750100': '油气开采',
                    '620300': '基础建设', '330100': '白色家电', '740100': '煤炭开采', '110700': '养殖业',
                    '750300': '炼化及贸易', '240300': '工业金属', '420900': '铁路公路', '340500': '白酒',
                    '410100': '电力', '730100': '通信服务', '620400': '专业工程', '420800': '物流',
                    '410300': '燃气', '750200': '油服工程', '640500': '轨交设备', '350100': '纺织制造',
                    '450200': '贸易', '490100': '证券', '370400': '医药商业', '330400': '厨卫电器',
                    '720900': '出版', '640600': '工程机械', '110400': '饲料', '230500': '特钢',
                    '220200': '化学原料', '330300': '小家电', '340400': '食品加工', '490300': '多元金融',
                    '280500': '乘用车', '330200': '黑色家电', '220800': '农化制品', '340600': '非白酒',
                    '280400': '摩托车及其他', '350300': '饰品', '230300': '冶钢原料', '280200': '汽车零部件',
                    '240400': '贵金属', '340900': '调味发酵品', '360300': '家居用品', '340700': '饮料乳品',
                    '610100': '水泥', '760100': '环境治理', '220300': '化学制品', '630800': '电网设备',
                    '370200': '中药', '330500': '照明设备', '450700': '旅游零售', '460800': '专业服务',
                    '270500': '消费电子', '330600': '家电零部件', '630700': '电池', '340800': '休闲食品',
                    '240500': '小金属', '770100': '个护用品', '370600': '医疗服务', '610300': '装修建材',
                    '280600': '商用车', '370500': '医疗器械', '360200': '包装印刷', '460900': '酒店餐饮',
                    '620600': '工程咨询服务', '770200': '化妆品', '220600': '橡胶', '710100': '计算机设备',
                    '220400': '化学纤维', '360500': '文娱用品', '330700': '其他家电', '770300': '医疗美容',
                    '270200': '元件', '630600': '风电设备', '610200': '玻璃玻纤', '650400': '航海装备',
                    '640200': '专用设备', '240200': '金属新材料', '630300': '其他电源设备', '110900': '农业综合',
                    '730200': '通信设备', '110500': '农产品加工', '450600': '互联网电商', '110100': '种植业',
                    '640100': '通用设备', '630100': '电机', '270400': '其他电子', '450400': '专业连锁',
                    '270600': '电子化学品', '220900': '非金属材料', '220500': '塑料', '640700': '自动化设备',
                    '370300': '生物制品', '760200': '环保设备', '240600': '能源金属', '720700': '数字媒体',
                    '110800': '动物保健', '350200': '服装家纺', '650200': '航空装备', '370100': '化学制药',
                    '430300': '房地产服务', '461000': '旅游及景区', '720400': '游戏', '270300': '光学光电子',
                    '450300': '一般零售', '270100': '半导体', '720500': '广告营销', '280300': '汽车服务',
                    '650100': '航天装备', '710400': '软件开发', '650500': '军工电子', '710300': 'IT服务',
                    '421000': '航空机场', '510100': '综合', '650300': '地面兵装', '720600': '影视院线',
                    '461100': '教育', '460600': '体育', '721000': '电视广播', '110300': '林业',
                    '360100': '造纸', '230400': '普钢', '630500': '光伏设备', '110200': '渔业',
                    '620200': '装修装饰', '740200': '焦炭', '430100': '房地产开发'
            }
            
            df = pd.DataFrame(list(fallback_codes.items()), 
                            columns=['指数代码', '指数名称'])
            logger.info(f"使用预定义行业代码，共 {len(df)} 个行业")
            return df
    
    def get_industry_weekly_data_with_retry(self, code: str, weeks: int = None) -> pd.DataFrame:
        """
        带重试机制的数据获取
        
        Args:
            code: 行业代码
            weeks: 回看周数
            
        Returns:
            包含周线数据的DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                df = self.get_industry_weekly_data(code, weeks)
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次尝试获取 {code} 数据失败: {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"获取 {code} 数据失败，已重试 {self.retry_times} 次")
        return pd.DataFrame()
    
    def get_industry_weekly_data(self, code: str, weeks: int = None) -> pd.DataFrame:
        """
        获取单个行业的周线数据
        
        Args:
            code: 行业代码
            weeks: 回看周数，默认使用self.lookback_weeks
            
        Returns:
            包含周线数据的DataFrame
        """
        if weeks is None:
            weeks = self.lookback_weeks
            
        try:
            logger.debug(f"获取 {code} 的周线数据")
            
            # 使用正确的AkShare API获取申万行业指数周线数据
            df = ak.index_hist_sw(symbol=code, period="week")
            
            if df.empty:
                logger.warning(f"行业 {code} 数据为空")
                return pd.DataFrame()
            
            logger.debug(f"获取到 {code} 数据，共 {len(df)} 行，列名: {list(df.columns)}")
            
            # 数据预处理 - 处理API返回的数据格式
            # index_hist_sw返回的列名: ['代码', '日期', '收盘', '开盘', '最高', '最低', '成交量', '成交额']
            if '日期' not in df.columns or '收盘' not in df.columns:
                logger.error(f"行业 {code} 数据格式不正确，列名: {list(df.columns)}")
                return pd.DataFrame()
            
            # 转换日期格式并设置为索引
            df['日期'] = pd.to_datetime(df['日期'])
            df.set_index('日期', inplace=True)
            df.sort_index(inplace=True)
            
            # 确保收盘价为数值类型
            df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
            
            # 去除收盘价为空的行
            df = df.dropna(subset=['收盘'])
            
            if len(df) == 0:
                logger.warning(f"行业 {code} 收盘价数据全部为空")
                return pd.DataFrame()
            
            # 计算RSI
            df['rsi14'] = calculate_rsi(df['收盘'], period=self.rsi_period)
            
            # 只保留有RSI数据的行
            df = df.dropna(subset=['rsi14'])
            
            if len(df) < weeks:
                logger.warning(f"行业 {code} 数据不足，只有 {len(df)} 周，需要 {weeks} 周")
            
            # 只保留最近的指定周数
            result_df = df.tail(weeks) if len(df) >= weeks else df
            
            logger.debug(f"行业 {code} 最终返回 {len(result_df)} 周数据")
            return result_df
            
        except Exception as e:
            logger.error(f"获取行业 {code} 数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_volatility_layers(self, sigma_list: List[float]) -> Tuple[float, float]:
        """
        计算波动率分层的分位点
        
        Args:
            sigma_list: 所有行业的波动率列表
            
        Returns:
            (q1, q3): 分位点
        """
        q1_pct = self.volatility_quantiles['q1']
        q3_pct = self.volatility_quantiles['q3']
        
        q1 = np.percentile(sigma_list, q1_pct)
        q3 = np.percentile(sigma_list, q3_pct)
        
        logger.info(f"波动率分层: Q{q1_pct}={q1:.3f}, Q{q3_pct}={q3:.3f}")
        return q1, q3
    
    def get_layer_percentiles(self, sigma: float, q1: float, q3: float) -> Tuple[str, int, int]:
        """
        根据波动率确定分层和对应的极端分位数
        
        Args:
            sigma: 行业波动率
            q1: 低分位点
            q3: 高分位点
            
        Returns:
            (layer, pct_low, pct_high): 分层名称和极端分位数
        """
        extreme_thresholds = self.rsi_thresholds["极端阈值"]
        
        if sigma >= q3:
            layer = '高波动'
            pct_low = extreme_thresholds["高波动"]["超卖"]
            pct_high = extreme_thresholds["高波动"]["超买"]
        elif sigma < q1:
            layer = '低波动'
            pct_low = extreme_thresholds["低波动"]["超卖"]
            pct_high = extreme_thresholds["低波动"]["超买"]
        else:
            layer = '中波动'
            pct_low = extreme_thresholds["中波动"]["超卖"]
            pct_high = extreme_thresholds["中波动"]["超买"]
            
        return layer, pct_low, pct_high
    
    def calculate_single_industry_thresholds(self, rsi_series: pd.Series, 
                                           sigma: float, q1: float, q3: float) -> Dict:
        """
        计算单个行业的RSI阈值
        
        Args:
            rsi_series: RSI时间序列
            sigma: 行业波动率
            q1: 低分位点
            q3: 高分位点
            
        Returns:
            包含各种阈值的字典
        """
        layer, pct_low, pct_high = self.get_layer_percentiles(sigma, q1, q3)
        
        # 从配置文件获取普通阈值分位数
        normal_oversold = self.rsi_thresholds['普通超卖']
        normal_overbought = self.rsi_thresholds['普通超买']
        
        # 计算原始极端阈值
        raw_extreme_oversold = float(np.percentile(rsi_series, pct_low))
        raw_extreme_overbought = float(np.percentile(rsi_series, pct_high))
        
        # 获取对应波动分层的系数
        layer_coefficients = self.extreme_threshold_coefficients.get(layer, {
            "超卖系数": 1.0,
            "超买系数": 1.0
        })
        oversold_coefficient = layer_coefficients["超卖系数"]
        overbought_coefficient = layer_coefficients["超买系数"]
        
        # 计算调整后的极端阈值
        adjusted_extreme_oversold = raw_extreme_oversold * oversold_coefficient
        adjusted_extreme_overbought = raw_extreme_overbought * overbought_coefficient
        
        # 计算各种阈值
        thresholds = {
            'layer': layer,
            'volatility': float(sigma),
            'current_rsi': float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else np.nan,
            '普通超卖': float(np.percentile(rsi_series, normal_oversold)),
            '普通超买': float(np.percentile(rsi_series, normal_overbought)),
            '极端超卖': adjusted_extreme_oversold,
            '极端超买': adjusted_extreme_overbought,
            'data_points': len(rsi_series)
        }
        
        logger.debug(f"行业 {layer} 阈值计算完成，系数应用如下:")
        logger.debug(f"  原始极端超卖: {raw_extreme_oversold:.3f}, 系数: {oversold_coefficient}, 调整后: {adjusted_extreme_oversold:.3f}")
        logger.debug(f"  原始极端超买: {raw_extreme_overbought:.3f}, 系数: {overbought_coefficient}, 调整后: {adjusted_extreme_overbought:.3f}")
        
        return thresholds
    
    def calculate_all_thresholds(self) -> pd.DataFrame:
        """
        计算所有申万二级行业的RSI阈值
        
        Returns:
            包含所有行业阈值的DataFrame
        """
        logger.info("开始计算申万二级行业RSI阈值...")
        
        # 获取行业代码
        industry_df = self.get_sw_industry_codes()
        
        # 存储所有行业数据和波动率
        all_data = {}
        sigma_list = []
        
        # 第一轮：获取所有行业数据并计算波动率
        logger.info("第一轮：获取行业数据并计算波动率...")
        for idx, row in industry_df.iterrows():
            code = row['指数代码']
            name = row['指数名称']
            
            logger.info(f"处理行业: {code} - {name}")
            
            # 获取周线数据（带重试）
            df = self.get_industry_weekly_data_with_retry(code)
            
            if df.empty or len(df) < self.min_data_points:
                logger.warning(f"跳过行业 {code}，数据不足（需要至少{self.min_data_points}周）")
                continue
            
            # 计算波动率
            rsi_series = df['rsi14'].dropna()
            if len(rsi_series) < self.min_rsi_points:
                logger.warning(f"跳过行业 {code}，RSI数据不足（需要至少{self.min_rsi_points}个数据点）")
                continue
                
            sigma = rsi_series.std()
            
            all_data[code] = {
                'name': name,
                'rsi_series': rsi_series,
                'sigma': sigma
            }
            sigma_list.append(sigma)
        
        if not sigma_list:
            raise ValueError("没有获取到有效的行业数据")
        
        logger.info(f"成功获取 {len(sigma_list)} 个行业的数据")
        
        # 计算波动率分层
        q1, q3 = self.calculate_volatility_layers(sigma_list)
        
        # 第二轮：计算各行业阈值
        logger.info("第二轮：计算各行业RSI阈值...")
        results = {}
        
        for code, data in all_data.items():
            name = data['name']
            rsi_series = data['rsi_series']
            sigma = data['sigma']
            
            logger.debug(f"计算 {code} - {name} 的阈值")
            
            # 计算阈值
            thresholds = self.calculate_single_industry_thresholds(
                rsi_series, sigma, q1, q3
            )
            thresholds['行业名称'] = name
            
            results[code] = thresholds
        
        # 转换为DataFrame
        result_df = pd.DataFrame.from_dict(results, orient='index')
        result_df.index.name = '行业代码'
        
        # 重新排列列的顺序
        columns_order = [
            '行业名称', 'layer', 'volatility', 'current_rsi',
            '普通超卖', '普通超买', '极端超卖', '极端超买', 'data_points'
        ]
        result_df = result_df[columns_order]
        
        logger.info(f"成功计算 {len(result_df)} 个行业的RSI阈值")
        return result_df
    
    def save_thresholds(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        保存阈值到CSV文件
        
        Args:
            df: 阈值DataFrame
            filename: 文件名，默认使用配置文件中的名称
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            filename = self.output_config['output_filename']
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 添加更新时间列和配置信息
        df_copy = df.copy()
        df_copy['更新时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if self.output_config['include_debug_info']:
            # 添加配置信息作为注释（在文件开头）
            config_info = [
                f"# 配置参数: 历史周数={self.lookback_weeks}, RSI周期={self.rsi_period}",
                f"# 普通阈值: 超卖{self.rsi_thresholds['普通超卖']}%, 超买{self.rsi_thresholds['普通超买']}%",
                f"# 极端阈值: 高波动({self.rsi_thresholds['极端阈值']['高波动']['超卖']}%,{self.rsi_thresholds['极端阈值']['高波动']['超买']}%), " +
                f"中波动({self.rsi_thresholds['极端阈值']['中波动']['超卖']}%,{self.rsi_thresholds['极端阈值']['中波动']['超买']}%), " +
                f"低波动({self.rsi_thresholds['极端阈值']['低波动']['超卖']}%,{self.rsi_thresholds['极端阈值']['低波动']['超买']}%)"
            ]
        
        # 保存到CSV（覆盖已存在的文件）
        precision = self.output_config['float_precision']
        df_copy.to_csv(filepath, encoding='utf-8-sig', float_format=f'%.{precision}f')
        
        logger.info(f"阈值已保存到: {filepath}")
        return filepath
    
    def run(self, save_file: bool = True) -> pd.DataFrame:
        """
        运行完整的阈值计算流程
        
        Args:
            save_file: 是否保存到文件
            
        Returns:
            计算结果DataFrame
        """
        try:
            # 计算阈值
            result_df = self.calculate_all_thresholds()
            
            # 保存文件
            if save_file:
                self.save_thresholds(result_df)
            
            # 打印统计信息
            self.print_summary(result_df)
            
            return result_df
            
        except Exception as e:
            logger.error(f"计算过程中出现错误: {e}")
            raise
    
    def print_summary(self, df: pd.DataFrame):
        """打印计算结果摘要"""
        logger.info("\n" + "="*50)
        logger.info("申万二级行业RSI阈值计算完成")
        logger.info("="*50)
        logger.info(f"总行业数量: {len(df)}")
        
        # 按波动率分层统计
        layer_counts = df['layer'].value_counts()
        logger.info("\n波动率分层统计:")
        for layer, count in layer_counts.items():
            logger.info(f"  {layer}: {count} 个行业")
        
        # 阈值统计
        logger.info(f"\n阈值统计:")
        logger.info(f"  普通超卖阈值范围: {df['普通超卖'].min():.1f} - {df['普通超卖'].max():.1f}")
        logger.info(f"  普通超买阈值范围: {df['普通超买'].min():.1f} - {df['普通超买'].max():.1f}")
        logger.info(f"  极端超卖阈值范围: {df['极端超卖'].min():.1f} - {df['极端超卖'].max():.1f}")
        logger.info(f"  极端超买阈值范围: {df['极端超买'].min():.1f} - {df['极端超买'].max():.1f}")
        
        logger.info("="*50)


def main():
    """主函数"""
    # 创建计算器实例
    calculator = SWIndustryRSIThresholds()
    
    # 运行计算
    result_df = calculator.run()
    
    # 显示前几行结果
    print("\n前10个行业的阈值:")
    print(result_df.head(10).to_string())


if __name__ == "__main__":
    main()