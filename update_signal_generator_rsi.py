"""
更新信号生成器以使用增强版RSI阈值加载器
"""

import re

def update_signal_generator():
    """更新信号生成器的RSI阈值获取逻辑"""
    
    # 读取原文件
    with open('strategy/signal_generator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换RSI阈值获取逻辑
    old_pattern = r'''            # 获取行业特定的RSI阈值
            rsi_overbought = self\.params\['rsi_overbought'\]  # 默认阈值
            rsi_oversold = self\.params\['rsi_oversold'\]      # 默认阈值
            
            if stock_code:
                try:
                    # 使用缓存的行业信息获取方法
                    industry = self\._get_stock_industry_cached\(stock_code\)
                    
                    # 优先使用CSV配置的RSI阈值
                    if industry:
                        try:
                            rsi_loader = get_rsi_loader\(\)
                            rsi_thresholds = rsi_loader\.get_rsi_thresholds\(industry\)
                            rsi_overbought = rsi_thresholds\['overbought'\]
                            rsi_oversold = rsi_thresholds\['oversold'\]
                            self\.logger\.debug\(f"股票 \{stock_code\} 行业 \{industry\} CSV RSI阈值: 超买=\{rsi_overbought\}, 超卖=\{rsi_oversold\}"\)
                        except Exception as csv_e:
                            self\.logger\.warning\(f"从CSV加载行业 \{industry\} RSI阈值失败: \{csv_e\}，尝试使用旧配置"\)
                            # 回退到旧的行业规则
                            industry_rules = self\._get_industry_rules_cached\(industry\)
                            if industry_rules:
                                rsi_overbought = industry_rules\['rsi_thresholds'\]\['overbought'\]
                                rsi_oversold = industry_rules\['rsi_thresholds'\]\['oversold'\]
                                self\.logger\.debug\(f"股票 \{stock_code\} 行业 \{industry\} 旧配置RSI阈值: 超买=\{rsi_overbought\}, 超卖=\{rsi_oversold\}"\)
                except Exception as e:
                    self\.logger\.warning\(f"获取股票 \{stock_code\} 行业RSI阈值失败: \{e\}，使用默认阈值"\)'''
    
    new_pattern = '''            # 获取行业特定的RSI阈值 - 使用增强版加载器
            rsi_overbought = self.params['rsi_overbought']  # 默认阈值
            rsi_oversold = self.params['rsi_oversold']      # 默认阈值
            
            if stock_code:
                try:
                    # 使用缓存的行业信息获取方法
                    industry = self._get_stock_industry_cached(stock_code)
                    
                    # 优先使用增强版RSI阈值加载器（动态计算的阈值）
                    if industry:
                        try:
                            enhanced_loader = get_enhanced_rsi_loader()
                            rsi_thresholds = enhanced_loader.get_rsi_thresholds(industry, use_extreme=False)
                            rsi_overbought = rsi_thresholds['overbought']
                            rsi_oversold = rsi_thresholds['oversold']
                            self.logger.debug(f"股票 {stock_code} 行业 {industry} 动态RSI阈值: 超买={rsi_overbought:.2f}, 超卖={rsi_oversold:.2f}")
                        except Exception as enhanced_e:
                            self.logger.warning(f"从增强版加载器获取行业 {industry} RSI阈值失败: {enhanced_e}，回退到原有配置")
                            # 回退到原有的CSV配置
                            try:
                                rsi_loader = get_rsi_loader()
                                rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)
                                rsi_overbought = rsi_thresholds['overbought']
                                rsi_oversold = rsi_thresholds['oversold']
                                self.logger.debug(f"股票 {stock_code} 行业 {industry} 静态RSI阈值: 超买={rsi_overbought}, 超卖={rsi_oversold}")
                            except Exception as csv_e:
                                self.logger.warning(f"从静态配置加载行业 {industry} RSI阈值也失败: {csv_e}，使用默认阈值")
                except Exception as e:
                    self.logger.warning(f"获取股票 {stock_code} 行业RSI阈值失败: {e}，使用默认阈值")'''
    
    # 执行替换
    updated_content = re.sub(old_pattern, new_pattern, content, flags=re.DOTALL)
    
    # 检查是否成功替换
    if updated_content == content:
        print("⚠️ 未找到匹配的模式，尝试手动定位...")
        # 查找关键位置
        if "# 获取行业特定的RSI阈值" in content:
            print("✅ 找到RSI阈值获取部分")
            # 手动替换关键部分
            lines = content.split('\n')
            new_lines = []
            in_rsi_section = False
            skip_lines = 0
            
            for i, line in enumerate(lines):
                if skip_lines > 0:
                    skip_lines -= 1
                    continue
                    
                if "# 获取行业特定的RSI阈值" in line:
                    in_rsi_section = True
                    new_lines.append("            # 获取行业特定的RSI阈值 - 使用增强版加载器")
                    continue
                
                if in_rsi_section and "rsi_overbought = self.params['rsi_overbought']" in line:
                    # 替换整个RSI阈值获取逻辑
                    new_lines.extend([
                        "            rsi_overbought = self.params['rsi_overbought']  # 默认阈值",
                        "            rsi_oversold = self.params['rsi_oversold']      # 默认阈值",
                        "            ",
                        "            if stock_code:",
                        "                try:",
                        "                    # 使用缓存的行业信息获取方法",
                        "                    industry = self._get_stock_industry_cached(stock_code)",
                        "                    ",
                        "                    # 优先使用增强版RSI阈值加载器（动态计算的阈值）",
                        "                    if industry:",
                        "                        try:",
                        "                            enhanced_loader = get_enhanced_rsi_loader()",
                        "                            rsi_thresholds = enhanced_loader.get_rsi_thresholds(industry, use_extreme=False)",
                        "                            rsi_overbought = rsi_thresholds['overbought']",
                        "                            rsi_oversold = rsi_thresholds['oversold']",
                        "                            self.logger.debug(f\"股票 {stock_code} 行业 {industry} 动态RSI阈值: 超买={rsi_overbought:.2f}, 超卖={rsi_oversold:.2f}\")",
                        "                        except Exception as enhanced_e:",
                        "                            self.logger.warning(f\"从增强版加载器获取行业 {industry} RSI阈值失败: {enhanced_e}，回退到原有配置\")",
                        "                            # 回退到原有的CSV配置",
                        "                            try:",
                        "                                rsi_loader = get_rsi_loader()",
                        "                                rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)",
                        "                                rsi_overbought = rsi_thresholds['overbought']",
                        "                                rsi_oversold = rsi_thresholds['oversold']",
                        "                                self.logger.debug(f\"股票 {stock_code} 行业 {industry} 静态RSI阈值: 超买={rsi_overbought}, 超卖={rsi_oversold}\")",
                        "                            except Exception as csv_e:",
                        "                                self.logger.warning(f\"从静态配置加载行业 {industry} RSI阈值也失败: {csv_e}，使用默认阈值\")",
                        "                except Exception as e:",
                        "                    self.logger.warning(f\"获取股票 {stock_code} 行业RSI阈值失败: {e}，使用默认阈值\")"
                    ])
                    
                    # 跳过原有的相关行
                    j = i + 1
                    while j < len(lines) and (
                        "rsi_oversold = self.params['rsi_oversold']" in lines[j] or
                        "if stock_code:" in lines[j] or
                        "industry = self._get_stock_industry_cached(stock_code)" in lines[j] or
                        "if industry:" in lines[j] or
                        "rsi_loader = get_rsi_loader()" in lines[j] or
                        "rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)" in lines[j] or
                        "rsi_overbought = rsi_thresholds['overbought']" in lines[j] or
                        "rsi_oversold = rsi_thresholds['oversold']" in lines[j] or
                        "self.logger.debug(f\"股票 {stock_code} 行业 {industry} CSV RSI阈值" in lines[j] or
                        "except Exception as csv_e:" in lines[j] or
                        "self.logger.warning(f\"从CSV加载行业 {industry} RSI阈值失败" in lines[j] or
                        "# 回退到旧的行业规则" in lines[j] or
                        "industry_rules = self._get_industry_rules_cached(industry)" in lines[j] or
                        "if industry_rules:" in lines[j] or
                        "rsi_overbought = industry_rules['rsi_thresholds']['overbought']" in lines[j] or
                        "rsi_oversold = industry_rules['rsi_thresholds']['oversold']" in lines[j] or
                        "self.logger.debug(f\"股票 {stock_code} 行业 {industry} 旧配置RSI阈值" in lines[j] or
                        "except Exception as e:" in lines[j] or
                        "self.logger.warning(f\"获取股票 {stock_code} 行业RSI阈值失败" in lines[j] or
                        lines[j].strip().startswith("try:") or
                        lines[j].strip().startswith("# 优先使用CSV配置") or
                        lines[j].strip() == ""
                    ):
                        j += 1
                    skip_lines = j - i - 1
                    in_rsi_section = False
                    continue
                
                new_lines.append(line)
            
            updated_content = '\n'.join(new_lines)
        else:
            print("❌ 未找到RSI阈值获取部分")
            return False
    
    # 写入更新后的文件
    with open('strategy/signal_generator.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ 信号生成器已更新为使用增强版RSI阈值加载器")
    return True

if __name__ == "__main__":
    update_signal_generator()