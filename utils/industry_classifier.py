#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业分类器模块
自动识别股票所属的申万二级行业
"""

import akshare as ak
import pandas as pd
import logging
from typing import Optional, Dict, Any
import time
import re

logger = logging.getLogger(__name__)

class IndustryClassifier:
    """股票行业自动分类器"""
    
    def __init__(self):
        self.cache = {}  # 缓存已查询的结果
        self.sw_industry_mapping = self._load_sw_industry_mapping()
    
    def _load_sw_industry_mapping(self) -> Dict[str, str]:
        """加载申万行业分类映射表"""
        import json
        import os
        
        # 尝试加载本地缓存的股票行业映射文件
        mapping_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                  'data_cache', 'stock_to_industry_map.json')
        
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'mapping' in data:
                        # 转换为简单的 {股票代码: 行业名称} 映射
                        stock_industry_map = {}
                        for stock_code, info in data['mapping'].items():
                            stock_industry_map[stock_code] = info['industry_name']
                        
                        logger.info(f"✅ 成功加载本地行业映射文件，包含 {len(stock_industry_map)} 只股票")
                        return stock_industry_map
            except Exception as e:
                logger.warning(f"加载本地行业映射文件失败: {e}")
        
        logger.warning("未找到本地行业映射文件，将使用网络查询（性能较低）")
        return {}
    
    def get_stock_industry_auto(self, stock_code: str) -> Optional[str]:
        """
        自动获取股票的申万二级行业分类
        
        Args:
            stock_code: 股票代码，如 '600900'
            
        Returns:
            申万二级行业名称，如 '电力'
        """
        # 检查缓存
        if stock_code in self.cache:
            return self.cache[stock_code]
        
        # 优先使用本地映射文件（高性能）
        if stock_code in self.sw_industry_mapping:
            industry = self.sw_industry_mapping[stock_code]
            self.cache[stock_code] = industry
            logger.debug(f"📋 从本地映射获取 {stock_code} 行业: {industry}")
            return industry
        
        # 如果本地映射中没有，才进行网络查询（低性能）
        logger.warning(f"⚠️ 股票 {stock_code} 不在本地映射中，将进行网络查询（较慢）")
        
        try:
            # 方法1: 通过akshare获取股票基本信息
            industry = self._get_industry_from_akshare(stock_code)
            if industry:
                self.cache[stock_code] = industry
                return industry
            
            # 方法2: 通过股票代码规律推断
            industry = self._infer_industry_from_code(stock_code)
            if industry:
                self.cache[stock_code] = industry
                return industry
            
            # 方法3: 通过股票名称关键词推断
            industry = self._infer_industry_from_name(stock_code)
            if industry:
                self.cache[stock_code] = industry
                return industry
                
        except Exception as e:
            logger.warning(f"获取股票 {stock_code} 行业信息失败: {e}")
        
        return None
    
    def _get_industry_from_akshare(self, stock_code: str) -> Optional[str]:
        """通过akshare获取行业信息"""
        try:
            # 获取股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            if stock_info is not None and not stock_info.empty:
                # 查找行业相关信息
                for _, row in stock_info.iterrows():
                    item = row['item']
                    value = row['value']
                    
                    if '行业' in item or 'Industry' in item:
                        # 将通用行业名称映射到申万二级行业
                        sw_industry = self._map_to_sw_industry(value)
                        if sw_industry:
                            logger.info(f"通过akshare获取到 {stock_code} 的行业: {value} -> {sw_industry}")
                            return sw_industry
            
            # 尝试获取申万行业分类
            time.sleep(0.1)  # 避免请求过快
            sw_info = ak.stock_board_industry_name_em()
            if sw_info is not None and not sw_info.empty:
                # 查找该股票在申万分类中的位置
                for _, board_row in sw_info.iterrows():
                    board_name = board_row['板块名称']
                    try:
                        # 获取板块成分股
                        constituents = ak.stock_board_industry_cons_em(symbol=board_name)
                        if constituents is not None and not constituents.empty:
                            if stock_code in constituents['代码'].values:
                                sw_industry = self._normalize_sw_industry_name(board_name)
                                logger.info(f"在申万分类中找到 {stock_code}: {board_name} -> {sw_industry}")
                                return sw_industry
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"akshare获取 {stock_code} 行业信息失败: {e}")
        
        return None
    
    def _infer_industry_from_code(self, stock_code: str) -> Optional[str]:
        """通过股票代码规律推断行业"""
        try:
            # 获取股票名称
            stock_info = ak.tool_trade_date_hist_sina()  # 这里应该用获取股票名称的API
            # 由于API限制，这里简化处理
            return None
        except:
            return None
    
    def _infer_industry_from_name(self, stock_code: str) -> Optional[str]:
        """通过股票名称关键词推断行业"""
        try:
            # 获取股票名称
            stock_info = ak.stock_zh_a_spot_em()
            if stock_info is not None and not stock_info.empty:
                stock_row = stock_info[stock_info['代码'] == stock_code]
                if not stock_row.empty:
                    stock_name = stock_row.iloc[0]['名称']
                    
                    # 基于名称关键词的行业推断规则
                    industry_keywords = {
                        '电力': ['电力', '电网', '发电', '水电', '火电', '核电', '新能源'],
                        '银行': ['银行', '农商', '城商', '股份制'],
                        '保险': ['保险', '人寿', '财险', '太保'],
                        '证券': ['证券', '投资', '信托'],
                        '房地产开发': ['地产', '房地产', '置业', '发展', '建设'],
                        '钢铁': ['钢铁', '特钢', '不锈钢'],
                        '煤炭开采': ['煤炭', '煤业', '焦煤'],
                        '石油化工': ['石化', '化工', '石油'],
                        '有色金属': ['有色', '铜业', '铝业', '锌业'],
                        '汽车整车': ['汽车', '客车', '货车'],
                        '食品制造': ['食品', '乳业', '肉类'],
                        '饮料制造': ['饮料', '啤酒', '白酒', '葡萄酒'],
                        '医药制造': ['医药', '制药', '生物', '疫苗'],
                        '纺织制造': ['纺织', '服装', '印染'],
                        '机械设备': ['机械', '设备', '重工'],
                        '电子': ['电子', '科技', '半导体', '芯片'],
                        '通信设备': ['通信', '网络', '光纤'],
                        '软件开发': ['软件', '信息', '数据', '云计算'],
                        '交通运输': ['运输', '物流', '航空', '港口'],
                        '建筑建材': ['建筑', '建材', '水泥', '玻璃'],
                        '农林牧渔': ['农业', '渔业', '牧业', '种业'],
                        '商贸零售': ['商贸', '零售', '百货', '超市'],
                        '休闲服务': ['旅游', '酒店', '餐饮', '娱乐'],
                        '传媒': ['传媒', '广告', '影视', '出版'],
                        '公用事业': ['公用', '供水', '供气', '环保']
                    }
                    
                    for industry, keywords in industry_keywords.items():
                        for keyword in keywords:
                            if keyword in stock_name:
                                logger.info(f"通过名称关键词推断 {stock_code}({stock_name}) 的行业: {industry}")
                                return industry
                                
        except Exception as e:
            logger.debug(f"通过名称推断 {stock_code} 行业失败: {e}")
        
        return None
    
    def _map_to_sw_industry(self, general_industry: str) -> Optional[str]:
        """将通用行业名称映射到申万二级行业"""
        mapping = {
            # 电力相关
            '电力': '电力',
            '电力行业': '电力',
            '公用事业': '电力',
            '新能源': '新能源设备',
            
            # 金融相关
            '银行': '银行',
            '银行业': '银行',
            '保险': '保险',
            '保险业': '保险',
            '证券': '证券',
            '证券业': '证券',
            
            # 房地产
            '房地产': '房地产开发',
            '房地产业': '房地产开发',
            
            # 工业
            '钢铁': '钢铁',
            '钢铁行业': '钢铁',
            '有色金属': '工业金属',
            '煤炭': '煤炭开采',
            '石油化工': '石油化工',
            '化工': '化学制品',
            
            # 消费
            '食品饮料': '食品制造',
            '食品': '食品制造',
            '饮料': '饮料制造',
            '医药': '化学制药',
            '医药生物': '化学制药',
            
            # 科技
            '电子': '消费电子',
            '计算机': '计算机应用',
            '通信': '通信设备',
            '软件': '软件开发',
            
            # 其他
            '汽车': '汽车整车',
            '机械': '专用设备',
            '建筑': '专业工程',
            '交通运输': '公路运输',
            '农业': '种植业',
            '商贸': '贸易',
            '传媒': '文化传媒'
        }
        
        return mapping.get(general_industry)
    
    def _normalize_sw_industry_name(self, board_name: str) -> str:
        """标准化申万行业名称"""
        # 移除常见的后缀
        suffixes_to_remove = ['板块', '行业', 'Ⅰ', 'Ⅱ', 'I', 'II']
        normalized = board_name
        for suffix in suffixes_to_remove:
            normalized = normalized.replace(suffix, '')
        return normalized.strip()
    
    def batch_classify(self, stock_codes: list) -> Dict[str, str]:
        """批量分类股票行业"""
        results = {}
        for stock_code in stock_codes:
            industry = self.get_stock_industry_auto(stock_code)
            if industry:
                results[stock_code] = industry
            time.sleep(0.1)  # 避免请求过快
        return results
    
    def update_mapping_file(self, new_mappings: Dict[str, str], 
                           mapping_file: str = 'config/stock_industry_mapping.py'):
        """更新映射文件"""
        try:
            # 读取现有映射
            with open(mapping_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 找到STOCK_INDUSTRY_MAPPING字典的位置
            import re
            pattern = r'STOCK_INDUSTRY_MAPPING\s*=\s*\{([^}]*)\}'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                # 解析现有映射
                existing_dict_str = match.group(1)
                
                # 构建新的映射字符串
                new_entries = []
                for code, industry in new_mappings.items():
                    new_entries.append(f'    "{code}": "{industry}",')
                
                # 插入新条目
                if existing_dict_str.strip():
                    new_dict_str = existing_dict_str.rstrip() + '\n' + '\n'.join(new_entries)
                else:
                    new_dict_str = '\n' + '\n'.join(new_entries) + '\n'
                
                # 替换内容
                new_content = content.replace(match.group(1), new_dict_str)
                
                # 写回文件
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"成功更新 {len(new_mappings)} 个股票的行业映射")
                
        except Exception as e:
            logger.error(f"更新映射文件失败: {e}")


# 全局实例
industry_classifier = IndustryClassifier()

def get_stock_industry_auto(stock_code: str) -> Optional[str]:
    """
    自动获取股票行业分类的便捷函数
    
    Args:
        stock_code: 股票代码
        
    Returns:
        申万二级行业名称
    """
    return industry_classifier.get_stock_industry_auto(stock_code)


if __name__ == "__main__":
    # 测试代码
    classifier = IndustryClassifier()
    
    # 测试一些股票
    test_stocks = ['600900', '000858', '000001', '000002', '600519']
    
    print("🔍 测试自动行业识别:")
    print("=" * 50)
    
    for stock in test_stocks:
        industry = classifier.get_stock_industry_auto(stock)
        print(f"📊 {stock}: {industry if industry else '未识别'}")
        time.sleep(0.5)  # 避免请求过快