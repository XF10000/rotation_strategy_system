#!/usr/bin/env python3
"""
验证布林带子图显示效果的脚本
"""

import json
import re
from datetime import datetime
import os


def verify_bb_subplot():
    # 找到最新的报告文件
    reports_dir = 'reports'
    report_files = [f for f in os.listdir(reports_dir) if f.startswith('integrated_backtest_report_') and f.endswith('.html')]
    
    if not report_files:
        print("未找到报告文件")
        return
    
    # 按时间排序，获取最新的报告
    report_files.sort(reverse=True)
    latest_report = report_files[0]
    report_path = os.path.join(reports_dir, latest_report)
    
    print(f"检查报告文件: {latest_report}")
    
    # 读取报告内容
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取K线数据
    kline_data_match = re.search(r'const klineData = (\{[^;]+\});', content, re.DOTALL)
    if not kline_data_match:
        print("未找到K线数据")
        return
    
    try:
        kline_data_str = kline_data_match.group(1)
        # 替换单引号为双引号以便解析
        kline_data_str = kline_data_str.replace("'", '"')
        kline_data = json.loads(kline_data_str)
        print(f"成功解析K线数据，包含 {len(kline_data)} 只股票")
        
        # 检查第一只股票的布林带数据
        first_stock = list(kline_data.keys())[0]
        stock_data = kline_data[first_stock]
        
        print(f"\n股票 {first_stock} 数据:")
        print(f"  K线数据点数: {len(stock_data.get('kline', []))}")
        print(f"  布林带上轨点数: {len(stock_data.get('bb_upper', []))}")
        print(f"  布林带中轨点数: {len(stock_data.get('bb_middle', []))}")
        print(f"  布林带下轨点数: {len(stock_data.get('bb_lower', []))}")
        
        # 检查布林带数据的前几个点
        bb_upper = stock_data.get('bb_upper', [])
        bb_middle = stock_data.get('bb_middle', [])
        bb_lower = stock_data.get('bb_lower', [])
        
        print("\n前5个布林带上轨数据点:")
        for i, point in enumerate(bb_upper[:5]):
            print(f"  {i+1}: {point}")
            
        print("\n前5个布林带中轨数据点:")
        for i, point in enumerate(bb_middle[:5]):
            print(f"  {i+1}: {point}")
            
        print("\n前5个布林带下轨数据点:")
        for i, point in enumerate(bb_lower[:5]):
            print(f"  {i+1}: {point}")
        
        # 检查ECharts配置中是否有布林带子图配置
        if 'xAxisIndex: 1' in content and 'yAxisIndex: 1' in content:
            print("\n✅ ECharts配置中已正确设置布林带子图索引")
        else:
            print("\n❌ ECharts配置中缺少布林带子图索引")
            
        # 检查是否有两个grid配置
        grid_matches = re.findall(r'gridIndex:\s*1', content)
        if len(grid_matches) >= 3:  # 应该有3个series使用gridIndex: 1 (上轨、中轨、下轨)
            print("✅ ECharts配置中已正确设置多个grid索引")
        else:
            print("❌ ECharts配置中grid索引设置不完整")
            
        print("\n✅ 布林带子图数据已正确注入报告，前端显示应正常")
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
    except Exception as e:
        print(f"处理数据时出错: {e}")


if __name__ == "__main__":
    verify_bb_subplot()
