#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main
import logging

# 设置详细的日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yunlv_tracking.log', mode='w', encoding='utf-8')
    ]
)

def debug_yunlv_tracking():
    """专门跟踪云铝股份(000807)的持股数量变化"""
    print("🔍 开始跟踪云铝股份(000807)持股数量...")
    
    # 运行回测
    try:
        main()
        print("✅ 回测完成，请查看日志文件 yunlv_tracking.log")
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_yunlv_tracking()