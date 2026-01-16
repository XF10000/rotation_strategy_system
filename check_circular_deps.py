"""
检测循环依赖的简单脚本
"""
import ast
import os
from pathlib import Path
from collections import defaultdict

def get_imports(file_path):
    """提取文件中的import语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    except:
        return set()

def check_circular_dependencies():
    """检测循环依赖"""
    print("=" * 80)
    print("循环依赖检测")
    print("=" * 80)
    
    # 扫描所有Python文件
    modules = {}
    base_path = Path('.')
    
    for folder in ['backtest', 'strategy', 'services', 'data', 'indicators', 'config', 'utils']:
        folder_path = base_path / folder
        if folder_path.exists():
            for py_file in folder_path.rglob('*.py'):
                if '__pycache__' in str(py_file):
                    continue
                
                module_name = folder
                imports = get_imports(py_file)
                
                # 只关注项目内部的import
                internal_imports = {imp for imp in imports 
                                   if imp in ['backtest', 'strategy', 'services', 
                                             'data', 'indicators', 'config', 'utils']}
                
                if internal_imports:
                    if module_name not in modules:
                        modules[module_name] = set()
                    modules[module_name].update(internal_imports)
    
    # 检测循环依赖
    print("\n📊 模块依赖关系:")
    for module, deps in sorted(modules.items()):
        if deps:
            print(f"  {module} → {', '.join(sorted(deps))}")
    
    # 检测直接循环
    print("\n🔍 检测循环依赖:")
    circular = []
    for module, deps in modules.items():
        for dep in deps:
            if dep in modules and module in modules[dep]:
                pair = tuple(sorted([module, dep]))
                if pair not in circular:
                    circular.append(pair)
    
    if circular:
        print("  ❌ 发现循环依赖:")
        for a, b in circular:
            print(f"     {a} ↔ {b}")
    else:
        print("  ✅ 未发现直接循环依赖")
    
    # 检查依赖层级
    print("\n📋 依赖层级分析:")
    
    # 定义期望的层级
    expected_levels = {
        'config': 0,
        'utils': 0,
        'indicators': 1,
        'data': 1,
        'strategy': 2,
        'backtest': 2,
        'services': 3
    }
    
    violations = []
    for module, deps in modules.items():
        module_level = expected_levels.get(module, 999)
        for dep in deps:
            dep_level = expected_levels.get(dep, 999)
            if dep_level >= module_level and dep != module:
                violations.append(f"{module} (L{module_level}) → {dep} (L{dep_level})")
    
    if violations:
        print("  ⚠️ 发现层级违规:")
        for v in violations:
            print(f"     {v}")
    else:
        print("  ✅ 依赖层级正确")
    
    print("\n" + "=" * 80)
    
    return len(circular) == 0 and len(violations) == 0

if __name__ == '__main__':
    success = check_circular_dependencies()
    exit(0 if success else 1)
