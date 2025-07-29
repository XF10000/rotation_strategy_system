# 📦 安装指南

## 🐍 Python环境要求

- **Python版本**: 3.8 或更高版本
- **推荐版本**: Python 3.9 或 3.10

## 🚀 快速安装

### 1. 克隆或下载项目
```bash
# 如果使用Git
git clone <repository-url>
cd Rotation_Strategy_DeepSeek_3

# 或直接下载解压到本地目录
```

### 2. 创建虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. 安装依赖包
```bash
# 安装所有依赖
pip install -r requirements.txt

# 如果网络较慢，可使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## ⚠️ 特殊依赖安装说明

### TA-Lib 安装

TA-Lib 是技术分析库，安装可能需要额外步骤：

#### Windows 用户
```bash
# 方法1: 使用预编译包
pip install TA-Lib

# 方法2: 如果上述失败，下载whl文件
# 访问: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 下载对应Python版本的whl文件，然后:
pip install TA_Lib-0.4.25-cp39-cp39-win_amd64.whl
```

#### macOS 用户
```bash
# 使用Homebrew安装依赖
brew install ta-lib

# 然后安装Python包
pip install TA-Lib
```

#### Linux 用户
```bash
# Ubuntu/Debian
sudo apt-get install libta-lib-dev
pip install TA-Lib

# CentOS/RHEL
sudo yum install ta-lib-devel
pip install TA-Lib
```

## 🔧 验证安装

运行以下命令验证安装是否成功：

```bash
python -c "import pandas, numpy, akshare, talib; print('✅ 所有核心依赖安装成功!')"
```

## 🏃‍♂️ 运行系统

```bash
# 运行主程序
python main.py

# 或使用指定配置
python main.py --config conservative
```

## 📋 依赖包说明

### 核心依赖
- **pandas**: 数据处理和分析
- **numpy**: 数值计算
- **akshare**: 中国股票数据获取

### 技术分析
- **TA-Lib**: 技术指标计算
- **pandas-ta**: 额外技术指标

### 可视化
- **matplotlib**: 基础图表
- **plotly**: 交互式图表
- **seaborn**: 统计图表

### 其他工具
- **jinja2**: HTML模板引擎
- **openpyxl**: Excel文件处理
- **scipy**: 科学计算

## 🐛 常见问题

### 问题1: TA-Lib安装失败
**解决方案**: 
- Windows: 使用预编译的whl文件
- macOS: 先安装Homebrew，再安装ta-lib
- Linux: 安装系统级ta-lib开发包

### 问题2: akshare数据获取失败
**解决方案**:
- 检查网络连接
- 可能需要等待一段时间重试
- 确保使用最新版本的akshare

### 问题3: 内存不足
**解决方案**:
- 减少回测时间范围
- 减少股票池大小
- 增加系统内存

## 📞 技术支持

如果遇到安装问题，请：
1. 检查Python版本是否符合要求
2. 确保网络连接正常
3. 尝试使用国内镜像源
4. 查看错误日志获取详细信息

---

**注意**: 首次运行时系统会自动创建缓存目录和配置文件，这是正常现象。
