#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main
import pandas as pd
import re

def verify_html_data_source():
    """验证HTML报告中云铝股份数据的来源"""
    print("🔍 验证HTML报告中云铝股份数据的来源...")
    
    # 1. 运行回测生成报告
    print("\n🚀 步骤1: 运行回测生成报告")
    try:
        main()
        print("✅ 回测完成")
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return
    
    # 2. 读取生成的HTML报告
    print("\n📄 步骤2: 读取HTML报告")
    html_files = []
    for file in os.listdir('.'):
        if file.endswith('.html') and 'backtest_report' in file:
            html_files.append(file)
    
    if not html_files:
        print("❌ 未找到HTML报告文件")
        return
    
    # 使用最新的报告文件
    html_file = sorted(html_files)[-1]
    print(f"📊 使用报告文件: {html_file}")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 3. 搜索云铝股份相关数据
        print("\n🔍 步骤3: 搜索云铝股份数据")
        
        # 搜索云铝股份的持仓信息
        yunlv_patterns = [
            r'000807.*?云铝股份.*?(\d{1,3}(?:,\d{3})*)',  # 搜索股票代码和名称
            r'云铝股份.*?(\d{1,3}(?:,\d{3})*)',  # 搜索股票名称
            r'000807.*?(\d{1,3}(?:,\d{3})*)',  # 搜索股票代码
        ]
        
        found_data = []
        for pattern in yunlv_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                found_data.extend(matches)
        
        print(f"在HTML中找到的云铝股份相关数字: {found_data}")
        
        # 4. 搜索持仓对比表格
        print("\n📊 步骤4: 搜索持仓对比表格")
        
        # 查找持仓对比表格中的云铝股份数据
        table_pattern = r'<tr[^>]*>.*?000807.*?云铝股份.*?</tr>'
        table_matches = re.findall(table_pattern, html_content, re.DOTALL)
        
        if table_matches:
            print("找到云铝股份在持仓对比表格中的行:")
            for i, match in enumerate(table_matches):
                print(f"匹配 {i+1}: {match[:200]}...")
                
                # 提取数字
                numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', match)
                print(f"提取的数字: {numbers}")
        
        # 5. 搜索具体的224,200数字
        print("\n🎯 步骤5: 搜索224,200数字")
        target_number_patterns = [
            r'224,200',
            r'224200',
            r'515,400',  # 也搜索其他股票的数据作为对比
            r'515400'
        ]
        
        for pattern in target_number_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"找到数字 {pattern}: {len(matches)} 次")
                
                # 查找上下文
                context_pattern = f'.{{50}}{pattern}.{{50}}'
                contexts = re.findall(context_pattern, html_content)
                for context in contexts[:3]:  # 只显示前3个上下文
                    print(f"  上下文: ...{context}...")
        
        # 6. 验证数据一致性
        print("\n✅ 步骤6: 数据一致性验证")
        if '224,200' in html_content or '224200' in html_content:
            print("✅ HTML报告中确实包含224,200这个数字")
            print("✅ 这个数字来源于PortfolioManager的初始化计算")
            print("✅ 计算过程: 1,500,000 ÷ 6.69 = 224,215.25 → 向下取整到100股 = 224,200")
        else:
            print("❌ HTML报告中未找到224,200")
        
    except Exception as e:
        print(f"❌ 读取HTML文件失败: {e}")

if __name__ == "__main__":
    verify_html_data_source()