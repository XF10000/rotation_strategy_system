"""
申万二级行业RSI阈值计算演示（2021版）
使用申万2021版行业列表和模拟数据展示功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append('..')
from sw_rsi_thresholds.sw_industry_rsi_thresholds import SWIndustryRSIThresholds, calculate_rsi

def generate_mock_industry_data_2021(code: str, name: str, weeks: int = 104) -> pd.DataFrame:
    """
    生成模拟的申万2021版行业周线数据
    
    Args:
        code: 行业代码（6位数字）
        name: 行业名称
        weeks: 周数
        
    Returns:
        模拟的周线数据DataFrame
    """
    # 生成日期序列
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=weeks, freq='W')
    
    # 生成模拟价格数据（随机游走）
    np.random.seed(int(code) % 2**32)  # 使用代码作为随机种子，确保可重复
    
    # 根据行业特性设置不同的波动率
    if any(keyword in name for keyword in ['银行', '保险', '证券']):
        volatility = 0.025  # 金融行业波动较小
    elif any(keyword in name for keyword in ['软件', '半导体', '游戏', '消费电子']):
        volatility = 0.06   # 科技行业波动较大
    elif any(keyword in name for keyword in ['白酒', '医疗', '新能源']):
        volatility = 0.05   # 消费和医疗行业波动较大
    elif any(keyword in name for keyword in ['煤炭', '钢铁', '有色', '化工']):
        volatility = 0.045  # 周期性行业波动中等偏大
    elif any(keyword in name for keyword in ['电力', '燃气', '水务', '公用']):
        volatility = 0.02   # 公用事业波动小
    else:
        volatility = 0.035  # 其他行业中等波动
    
    # 生成价格序列
    returns = np.random.normal(0, volatility, weeks)
    prices = 1000 * np.exp(np.cumsum(returns))  # 从1000开始的几何布朗运动
    
    # 创建DataFrame
    df = pd.DataFrame({
        '日期': dates,
        '收盘': prices
    })
    df.set_index('日期', inplace=True)
    
    # 计算RSI
    df['rsi14'] = calculate_rsi(df['收盘'], period=14)
    
    return df


class MockSW2021IndustryRSIThresholds(SWIndustryRSIThresholds):
    """使用申万2021版行业列表和模拟数据的RSI阈值计算器"""
    
    def get_industry_weekly_data_with_retry(self, code: str, weeks: int = None) -> pd.DataFrame:
        """
        使用模拟数据替代真实API调用
        """
        if weeks is None:
            weeks = self.lookback_weeks
        
        # 使用预定义的行业名称映射
        industry_names = {
            '340500': '白酒',
            '410100': '电力',
            '270100': '半导体',
            '480200': '国有大型银行',
            '740100': '煤炭开采',
            '370100': '化学制药',
            '710400': '软件开发',
            '330100': '白色家电',
            '280500': '乘用车',
            '620100': '房屋建设',
            '450600': '互联网电商',
            '630600': '风电设备',
        }
        name = industry_names.get(code, '未知行业')
        
        print(f"生成 {code} - {name} 的模拟数据...")
        
        # 生成模拟数据
        df = generate_mock_industry_data_2021(code, name, weeks + 20)
        
        # 模拟一些数据质量问题
        if code in ['480500', '110300']:  # 农商行、林业数据不足
            return df.head(40)  # 只返回40周数据
        elif code in ['760200']:  # 环保设备数据异常
            # 模拟数据中有一些异常值
            df.loc[df.index[-10:], 'rsi14'] = np.nan
            return df.tail(weeks)
        
        return df.tail(weeks)


def demo_sw_2021_calculation():
    """演示申万2021版计算过程"""
    print("申万二级行业RSI阈值计算演示（2021版）")
    print("=" * 60)
    
    # 创建模拟计算器
    calculator = MockSW2021IndustryRSIThresholds()
    
    # 选择一些代表性行业进行演示
    demo_codes = [
        '340500',  # 白酒
        '410100',  # 电力  
        '270100',  # 半导体
        '480200',  # 国有大型银行
        '740100',  # 煤炭开采
        '370100',  # 化学制药
        '710400',  # 软件开发
        '330100',  # 白色家电
        '280500',  # 乘用车
        '620100',  # 房屋建设
        '450600',  # 互联网电商
        '630600',  # 风电设备
    ]
    
    # 创建演示用的行业DataFrame（使用预定义数据）
    industry_names = {
        '340500': '白酒',
        '410100': '电力',
        '270100': '半导体',
        '480200': '国有大型银行',
        '740100': '煤炭开采',
        '370100': '化学制药',
        '710400': '软件开发',
        '330100': '白色家电',
        '280500': '乘用车',
        '620100': '房屋建设',
        '450600': '互联网电商',
        '630600': '风电设备',
    }
    
    demo_industries = pd.DataFrame([
        {'指数代码': code, '指数名称': industry_names[code]} 
        for code in demo_codes
    ])
    
    print(f"选择 {len(demo_industries)} 个代表性行业进行演示:")
    for _, row in demo_industries.iterrows():
        print(f"  {row['指数代码']} - {row['指数名称']}")
    
    # 替换获取行业代码的方法
    calculator.get_sw_industry_codes = lambda: demo_industries
    
    try:
        # 运行计算
        result_df = calculator.run(save_file=True)
        
        print("\n计算结果:")
        print("=" * 80)
        print(result_df.to_string())
        
        # 分析结果
        print("\n结果分析:")
        print("-" * 40)
        
        # 按波动率分层统计
        layer_stats = result_df['layer'].value_counts()
        print(f"波动率分层分布:")
        for layer, count in layer_stats.items():
            print(f"  {layer}: {count} 个行业")
        
        # 不同分层的阈值对比
        print(f"\n各分层阈值对比:")
        for layer in ['低波动', '中波动', '高波动']:
            if layer in result_df['layer'].values:
                layer_data = result_df[result_df['layer'] == layer]
                print(f"\n{layer}行业 ({len(layer_data)}个):")
                print(f"  普通超卖阈值: {layer_data['普通超卖'].mean():.1f} (平均)")
                print(f"  普通超买阈值: {layer_data['普通超买'].mean():.1f} (平均)")
                print(f"  极端超卖阈值: {layer_data['极端超卖'].mean():.1f} (平均)")
                print(f"  极端超买阈值: {layer_data['极端超买'].mean():.1f} (平均)")
        
        # 展示具体行业的使用示例
        print(f"\n具体行业使用示例:")
        print("-" * 40)
        for i, (code, row) in enumerate(result_df.head(3).iterrows()):
            print(f"\n{i+1}. {code} - {row['行业名称']} ({row['layer']}):")
            print(f"   当前RSI: {row['current_rsi']:.1f}")
            
            # 判断当前状态
            if row['current_rsi'] <= row['极端超卖']:
                status = "极端超卖"
            elif row['current_rsi'] <= row['普通超卖']:
                status = "普通超卖"
            elif row['current_rsi'] >= row['极端超买']:
                status = "极端超买"
            elif row['current_rsi'] >= row['普通超买']:
                status = "普通超买"
            else:
                status = "正常区间"
            
            print(f"   当前状态: {status}")
            print(f"   阈值参考: 极端超卖({row['极端超卖']:.1f}) < 普通超卖({row['普通超卖']:.1f}) < 普通超买({row['普通超买']:.1f}) < 极端超买({row['极端超买']:.1f})")
        
        return result_df
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_sw_2021_industry_overview():
    """展示申万2021版行业概览"""
    print("\n" + "=" * 60)
    print("申万2021版行业分类概览")
    print("=" * 60)
    
    print("申万2021版包含124个二级行业")
    print("数据来源：AkShare API (sw_index_second_info)")
    
    print(f"\n按代码前缀分组:")
    prefix_names = {
        '11': '农林牧渔',
        '22': '化工',
        '23': '钢铁',
        '24': '有色金属',
        '27': '电子',
        '28': '汽车',
        '33': '家电',
        '34': '食品饮料',
        '35': '纺织服装',
        '36': '轻工制造',
        '37': '医药生物',
        '41': '公用事业',
        '42': '交通运输',
        '43': '房地产',
        '45': '商贸零售',
        '46': '社会服务',
        '48': '银行',
        '49': '非银金融',
        '51': '综合',
        '61': '建筑材料',
        '62': '建筑装饰',
        '63': '电力设备',
        '64': '机械设备',
        '65': '国防军工',
        '71': '计算机',
        '72': '传媒',
        '73': '通信',
        '74': '煤炭',
        '75': '石油石化',
        '76': '环保',
        '77': '美容护理'
    }
    
    for prefix, name in prefix_names.items():
        print(f"  {prefix}xx ({name})")
    
    # 显示一些示例
    print(f"\n行业示例:")
    sample_industries = [
        ('340500', '白酒'),
        ('410100', '电力'),
        ('270100', '半导体'),
        ('480200', '国有大型银行'),
        ('740100', '煤炭开采'),
        ('370100', '化学制药'),
        ('710400', '软件开发'),
        ('330100', '白色家电'),
        ('280500', '乘用车'),
        ('620100', '房屋建设')
    ]
    
    for code, name in sample_industries:
        print(f"  {code} - {name}")


if __name__ == "__main__":
    # 显示行业概览
    show_sw_2021_industry_overview()
    
    # 运行演示
    result_df = demo_sw_2021_calculation()
    
    if result_df is not None:
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        print("\n申万2021版RSI阈值计算系统特点:")
        print("1. 支持131个申万二级行业（2021版）")
        print("2. 基于行业波动率特性进行分层")
        print("3. 为不同波动率行业设置个性化阈值")
        print("4. 输出CSV文件供量化策略使用")
        print("5. 支持定期更新和历史回测")
        
        print(f"\n生成的CSV文件可直接用于:")
        print("- 行业轮动策略的RSI信号判断")
        print("- 个股选择时的行业背景分析")
        print("- 风险管理中的行业配置决策")
        print("- 量化回测中的动态阈值设定")
    else:
        print("演示失败，请检查代码和数据文件")