#!/usr/bin/env python3
"""
申万二级行业RSI阈值计算工具（2021版）
使用申万2021版行业分类标准
"""

import argparse
import sys
import os
from datetime import datetime
import pandas as pd

# 添加项目路径
sys.path.append('..')

from sw_rsi_thresholds.sw_industry_rsi_thresholds import SWIndustryRSIThresholds


def main():
    parser = argparse.ArgumentParser(
        description='申万二级行业RSI阈值计算工具（2021版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python3 run_sw_2021_rsi_calculation.py                    # 使用默认参数运行
  python3 run_sw_2021_rsi_calculation.py --demo             # 运行演示模式
  python3 run_sw_2021_rsi_calculation.py --output custom/   # 指定输出目录
  python3 run_sw_2021_rsi_calculation.py --weeks 52         # 使用1年历史数据
  python3 run_sw_2021_rsi_calculation.py --sample 20        # 只计算20个样本行业
        """
    )
    
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='输出目录 (默认: output)'
    )
    
    parser.add_argument(
        '--weeks', '-w',
        type=int,
        default=104,
        help='历史数据周数 (默认: 104周，约2年)'
    )
    
    parser.add_argument(
        '--rsi-period',
        type=int,
        default=14,
        help='RSI计算周期 (默认: 14)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='运行演示模式（使用模拟数据）'
    )
    
    parser.add_argument(
        '--sample',
        type=int,
        help='只计算指定数量的样本行业（用于测试）'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='不保存CSV文件，仅显示结果'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("申万二级行业RSI阈值计算工具（2021版）")
    print("=" * 60)
    
    # 显示申万2021版行业概览
    print(f"申万2021版行业总数: 124 个")
    print(f"数据来源: AkShare API (sw_index_second_info)")
    print(f"涵盖申万一级行业的所有二级分类")
    
    print(f"计算参数:")
    print(f"  输出目录: {args.output}")
    print(f"  历史周数: {args.weeks}")
    print(f"  RSI周期: {args.rsi_period}")
    print(f"  演示模式: {'是' if args.demo else '否'}")
    print(f"  样本数量: {args.sample if args.sample else '全部'}")
    print(f"  保存文件: {'否' if args.no_save else '是'}")
    print("=" * 60)
    
    try:
        if args.demo:
            # 运行演示模式
            print("运行演示模式...")
            from demo_sw_2021_rsi_thresholds import demo_sw_2021_calculation
            result_df = demo_sw_2021_calculation()
        else:
            # 运行真实计算
            calculator = SWIndustryRSIThresholds(output_dir=args.output)
            calculator.lookback_weeks = args.weeks
            calculator.rsi_period = args.rsi_period
            
            # 如果指定了样本数量，则限制行业数量
            if args.sample:
                original_method = calculator.get_sw_industry_codes
                def get_sample_industries():
                    full_df = original_method()
                    return full_df.sample(min(args.sample, len(full_df)))
                calculator.get_sw_industry_codes = get_sample_industries
                print(f"注意: 仅计算 {args.sample} 个样本行业")
            
            result_df = calculator.run(save_file=not args.no_save)
        
        if result_df is not None:
            print(f"\n✓ 成功计算 {len(result_df)} 个行业的RSI阈值")
            
            # 显示统计信息
            print("\n分层统计:")
            layer_counts = result_df['layer'].value_counts()
            for layer, count in layer_counts.items():
                print(f"  {layer}: {count} 个行业")
            
            # 显示阈值范围
            print("\n阈值范围:")
            print(f"  普通超卖: {result_df['普通超卖'].min():.1f} - {result_df['普通超卖'].max():.1f}")
            print(f"  普通超买: {result_df['普通超买'].min():.1f} - {result_df['普通超买'].max():.1f}")
            print(f"  极端超卖: {result_df['极端超卖'].min():.1f} - {result_df['极端超卖'].max():.1f}")
            print(f"  极端超买: {result_df['极端超买'].min():.1f} - {result_df['极端超买'].max():.1f}")
            
            # 显示一些具体行业示例
            print(f"\n行业示例:")
            for i, (code, row) in enumerate(result_df.head(5).iterrows()):
                status = "正常"
                if row['current_rsi'] <= row['极端超卖']:
                    status = "极端超卖"
                elif row['current_rsi'] <= row['普通超卖']:
                    status = "普通超卖"
                elif row['current_rsi'] >= row['极端超买']:
                    status = "极端超买"
                elif row['current_rsi'] >= row['普通超买']:
                    status = "普通超买"
                
                print(f"  {code} {row['行业名称']} ({row['layer']}): RSI={row['current_rsi']:.1f} [{status}]")
            
            if not args.no_save:
                print(f"\n✓ 结果已保存到 {args.output} 目录")
                
                # 显示文件使用说明
                print(f"\n使用说明:")
                print(f"1. CSV文件包含所有行业的动态RSI阈值")
                print(f"2. 可直接用于量化策略的信号判断")
                print(f"3. 建议每月更新一次阈值数据")
                print(f"4. 支持按行业代码快速查询阈值")
            
            print("\n✓ 计算完成！")
            return 0
        else:
            print("✗ 计算失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 1
    except Exception as e:
        print(f"\n✗ 计算过程中出现错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)