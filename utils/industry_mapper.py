"""
股票代码到申万二级行业的映射工具
生成并维护股票-行业映射缓存文件
"""

import akshare as ak
import pandas as pd
import json
import os
from typing import Dict, Optional
from datetime import datetime
import time

class IndustryMapper:
    """申万二级行业映射生成器"""
    
    def __init__(self, cache_dir: str = "utils"):
        """
        初始化映射生成器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "stock_to_industry_map.json")
        self.retry_times = 3
        self.retry_delay = 2  # 秒
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_shenwan_industries(self) -> pd.DataFrame:
        """
        获取申万二级行业列表
        
        Returns:
            pd.DataFrame: 包含行业代码和名称的DataFrame
        """
        print("📊 正在获取申万二级行业列表...")
        
        for attempt in range(self.retry_times):
            try:
                # 获取申万二级行业信息
                sw_industry = ak.sw_index_second_info()
                
                if sw_industry.empty:
                    raise ValueError("AkShare API返回空数据")
                
                # 处理数据格式
                df = sw_industry[['行业代码', '行业名称']].copy()
                df['行业代码'] = df['行业代码'].astype(str).str.replace('.SI', '')
                df = df.rename(columns={'行业代码': '指数代码', '行业名称': '指数名称'})
                df = df.drop_duplicates().sort_values('指数代码').reset_index(drop=True)
                
                print(f"✅ 成功获取 {len(df)} 个申万二级行业")
                return df
                
            except Exception as e:
                print(f"⚠️  第 {attempt + 1} 次尝试失败: {e}")
                if attempt < self.retry_times - 1:
                    print(f"🔄 等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    print("❌ 获取申万二级行业列表失败，使用备用数据")
                    return self._get_fallback_industries()
    
    def _get_fallback_industries(self) -> pd.DataFrame:
        """
        获取备用的申万二级行业列表（硬编码）
        
        Returns:
            pd.DataFrame: 备用行业列表
        """
        fallback_data = {
            '620100': '房屋建设', '620200': '装修装饰', '620300': '基础建设',
            '630100': '钢铁', '630200': '铝', '630300': '铜', '630400': '铅锌',
            '630500': '黄金', '630600': '工业金属', '630700': '贵金属',
            '640100': '煤炭开采', '640200': '石油开采', '640300': '天然气',
            '650100': '石油化工', '650200': '化学制品', '650300': '化学纤维',
            '650400': '化肥农药', '650500': '日用化工',
            # ... 更多行业代码（这里简化显示）
        }
        
        df = pd.DataFrame(list(fallback_data.items()), columns=['指数代码', '指数名称'])
        print(f"📋 使用备用数据，包含 {len(df)} 个行业")
        return df
    
    def get_industry_constituents(self, industry_code: str, industry_name: str) -> Optional[pd.DataFrame]:
        """
        获取指定行业的成分股
        
        Args:
            industry_code: 行业代码
            industry_name: 行业名称
            
        Returns:
            pd.DataFrame: 成分股信息，失败时返回None
        """
        for attempt in range(self.retry_times):
            try:
                # 获取行业成分股
                constituents = ak.index_component_sw(symbol=industry_code)
                
                if constituents.empty:
                    print(f"⚠️  行业 {industry_name}({industry_code}) 无成分股数据")
                    return None
                
                # 确保包含股票代码列
                if '证券代码' in constituents.columns:
                    constituents['股票代码'] = constituents['证券代码']
                elif '品种代码' in constituents.columns:
                    constituents['股票代码'] = constituents['品种代码']
                elif '代码' in constituents.columns:
                    constituents['股票代码'] = constituents['代码']
                elif 'symbol' in constituents.columns:
                    constituents['股票代码'] = constituents['symbol']
                else:
                    # 如果没有找到标准列名，使用第一列作为股票代码
                    constituents['股票代码'] = constituents.iloc[:, 0]
                
                # 清理股票代码格式
                constituents['股票代码'] = constituents['股票代码'].astype(str).str.strip()
                
                print(f"✅ {industry_name}({industry_code}): {len(constituents)} 只成分股")
                return constituents
                
            except Exception as e:
                print(f"⚠️  获取 {industry_name} 成分股第 {attempt + 1} 次尝试失败: {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    print(f"❌ 获取 {industry_name} 成分股失败")
                    return None
    
    def generate_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        生成完整的股票-行业映射
        
        Returns:
            Dict: 股票代码到行业信息的映射
        """
        print("🚀 开始生成股票-行业映射...")
        
        # 获取所有申万二级行业
        industries_df = self.get_shenwan_industries()
        
        stock_industry_map = {}
        total_industries = len(industries_df)
        processed_industries = 0
        total_stocks = 0
        
        for _, row in industries_df.iterrows():
            industry_code = row['指数代码']
            industry_name = row['指数名称']
            
            processed_industries += 1
            print(f"\n📈 处理进度: {processed_industries}/{total_industries} - {industry_name}")
            
            # 获取该行业的成分股
            constituents = self.get_industry_constituents(industry_code, industry_name)
            
            if constituents is not None:
                # 将成分股添加到映射中
                for _, stock_row in constituents.iterrows():
                    stock_code = stock_row['股票代码']
                    
                    # 跳过无效的股票代码
                    if pd.isna(stock_code) or stock_code == '' or stock_code == 'nan':
                        continue
                    
                    stock_industry_map[stock_code] = {
                        'industry_code': industry_code,
                        'industry_name': industry_name
                    }
                    total_stocks += 1
            
            # 添加小延时，避免API调用过于频繁
            time.sleep(0.5)
        
        print(f"\n🎉 映射生成完成！")
        print(f"📊 总计处理: {processed_industries} 个行业, {total_stocks} 只股票")
        
        return stock_industry_map
    
    def save_mapping(self, mapping: Dict[str, Dict[str, str]]) -> None:
        """
        保存映射到缓存文件
        
        Args:
            mapping: 股票-行业映射字典
        """
        try:
            # 添加元数据
            cache_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_stocks': len(mapping),
                    'version': '1.0'
                },
                'mapping': mapping
            }
            
            # 保存到JSON文件
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 映射已保存到: {self.cache_file}")
            print(f"📁 文件大小: {os.path.getsize(self.cache_file) / 1024:.1f} KB")
            
        except Exception as e:
            print(f"❌ 保存映射失败: {e}")
            raise
    
    def load_mapping(self) -> Optional[Dict[str, Dict[str, str]]]:
        """
        从缓存文件加载映射
        
        Returns:
            Dict: 股票-行业映射，失败时返回None
        """
        try:
            if not os.path.exists(self.cache_file):
                print(f"⚠️  缓存文件不存在: {self.cache_file}")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查数据格式
            if 'mapping' not in cache_data:
                print("⚠️  缓存文件格式不正确，缺少mapping字段")
                return None
            
            mapping = cache_data['mapping']
            metadata = cache_data.get('metadata', {})
            
            print(f"📂 成功加载缓存映射")
            print(f"📊 股票数量: {len(mapping)}")
            print(f"🕐 生成时间: {metadata.get('generated_at', '未知')}")
            
            return mapping
            
        except Exception as e:
            print(f"❌ 加载缓存失败: {e}")
            return None
    
    def run(self, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        """
        运行映射生成流程
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            Dict: 股票-行业映射
        """
        print("=" * 60)
        print("🏭 申万二级行业股票映射生成器")
        print("=" * 60)
        
        # 检查是否需要生成新映射
        if not force_refresh:
            existing_mapping = self.load_mapping()
            if existing_mapping is not None:
                print("✅ 使用现有缓存映射")
                return existing_mapping
        
        # 生成新映射
        print("🔄 开始生成新的映射...")
        mapping = self.generate_mapping()
        
        # 保存映射
        self.save_mapping(mapping)
        
        return mapping


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成股票-申万二级行业映射缓存')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制刷新缓存，即使已存在')
    parser.add_argument('--cache-dir', default='utils',
                       help='缓存目录路径 (默认: utils)')
    
    args = parser.parse_args()
    
    # 创建映射生成器并运行
    mapper = IndustryMapper(cache_dir=args.cache_dir)
    mapping = mapper.run(force_refresh=args.force)
    
    print(f"\n🎯 映射生成完成，共 {len(mapping)} 只股票")
    
    # 显示一些示例
    print("\n📋 映射示例:")
    for i, (stock_code, info) in enumerate(mapping.items()):
        if i >= 5:  # 只显示前5个
            break
        print(f"  {stock_code}: {info['industry_name']}({info['industry_code']})")
    
    if len(mapping) > 5:
        print(f"  ... 还有 {len(mapping) - 5} 只股票")


if __name__ == "__main__":
    main()
