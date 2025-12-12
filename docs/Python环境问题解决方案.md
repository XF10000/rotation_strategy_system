# Python 环境问题解决方案

## 问题描述

您的系统有两个 Python 环境：
1. **Homebrew Python**: `/opt/homebrew/bin/python3`
2. **Anaconda Python**: `/Volumes/Frank1T/opt/anaconda3/bin/python3`

当前 `pip` 安装到了 Anaconda 环境，但 `python3` 命令使用的是 Homebrew Python，导致包找不到。

---

## 解决方案一：使用 Anaconda Python（推荐）

### 步骤 1：安装缺失的包

```bash
# 安装 TA-Lib（如果还没安装）
/Volumes/Frank1T/opt/anaconda3/bin/pip install TA-Lib
```

### 步骤 2：使用 Anaconda Python 运行程序

```bash
# 方法 1：直接使用完整路径
/Volumes/Frank1T/opt/anaconda3/bin/python3 main.py

# 方法 2：创建别名（推荐）
alias python3='/Volumes/Frank1T/opt/anaconda3/bin/python3'
python3 main.py
```

### 步骤 3：永久设置（可选）

将别名添加到 `~/.zshrc`：

```bash
echo "alias python3='/Volumes/Frank1T/opt/anaconda3/bin/python3'" >> ~/.zshrc
source ~/.zshrc
```

---

## 解决方案二：使用 Homebrew Python

### 步骤 1：安装所有依赖包

```bash
# 使用 --break-system-packages 标志（不推荐但可用）
/opt/homebrew/bin/python3 -m pip install --break-system-packages tushare akshare TA-Lib pandas numpy
```

### 步骤 2：运行程序

```bash
python3 main.py
```

---

## 解决方案三：使用虚拟环境（最佳实践）

### 步骤 1：创建虚拟环境

```bash
cd /Volumes/Frank1T/VibeCoding/Rotation_Strategy_3_1
python3 -m venv venv
```

### 步骤 2：激活虚拟环境

```bash
source venv/bin/activate
```

### 步骤 3：安装依赖

```bash
pip install -r requirements.txt
# 或手动安装
pip install tushare akshare TA-Lib pandas numpy
```

### 步骤 4：运行程序

```bash
python3 main.py
```

### 步骤 5：退出虚拟环境

```bash
deactivate
```

---

## 快速修复（立即可用）

**最快的解决方案**：

```bash
# 1. 安装 TA-Lib 到 Anaconda
/Volumes/Frank1T/opt/anaconda3/bin/pip install TA-Lib

# 2. 使用 Anaconda Python 运行
/Volumes/Frank1T/opt/anaconda3/bin/python3 main.py
```

---

## 验证环境

检查当前使用的 Python 和已安装的包：

```bash
# 检查 Python 路径
which python3

# 检查已安装的包
python3 -m pip list | grep -E "tushare|akshare|TA-Lib"

# 测试导入
python3 -c "import tushare; import akshare; import talib; print('✅ 所有包都可用')"
```

---

## 推荐配置

我建议您使用 **Anaconda Python**，因为：
1. ✅ 已经安装了大部分科学计算包
2. ✅ 不需要 `--break-system-packages` 标志
3. ✅ 更适合数据分析和量化交易

---

## 当前状态

根据您的终端输出：
- ✅ Tushare 已安装在 Anaconda 环境
- ✅ Akshare 已安装在 Anaconda 环境
- ❌ TA-Lib 还需要安装到 Anaconda 环境

**立即执行**：

```bash
/Volumes/Frank1T/opt/anaconda3/bin/pip install TA-Lib
/Volumes/Frank1T/opt/anaconda3/bin/python3 main.py
```
