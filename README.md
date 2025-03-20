# 亚马逊商品竞品分析系统

### 项目背景
为呆呆狸定制的亚马逊竞品分析解决方案，实现商品图片自动采集、竞品判定和相似度计算（开发中）功能。系统通过Selenium自动化采集结合通义千问多模态分析，提供精准的竞品识别服务。

---

## 系统架构
```
.
├── main.py                 # 主爬虫程序
├── competitive_analysis.py # 竞品分析核心模块
├── get_my_product_name.py  # Excel数据解析器
├── get_keyword.py          # 关键词提取模块
├── analysis_config.py      # 配置文件
└── images/                 # 商品图片存储目录
```

---

## 功能模块

### 1. 智能爬虫系统 (main.py)
- 基于Selenium的浏览器自动化
- 反检测机制：
  - 随机操作延迟（1-3秒）
  - 动态User-Agent切换
  - 浏览器指纹伪装
- 图片下载：
  - 自动分类存储至`/images/{搜索关键词}`
  - 支持高分辨率图片捕获

### 2. 竞品分析引擎 (competitive_analysis.py)
- 多维度判定逻辑：
  - **图像特征分析**：使用通义千问VL模型进行：
    - 材质比对
    - 形状匹配
    - 灯泡特征识别
  - **文本匹配**：标题关键词校验
- 输出CSV格式分析报告

### 3. 数据预处理模块
- Excel词表解析 (get_my_product_name.py)
- 商品关键词提取 (get_keyword.py)

---

## 快速开始

### 环境要求
```bash
Python 3.8+ 
必需组件：pip install selenium pandas dashscope openai
浏览器要求：Chrome + 对应版本chromedriver
```

### 配置步骤
1. 修改API配置
```python
# analysis_config.py
API_KEY = 'sk-your-api-key-here'  # 通义千问API密钥
```

2. 准备数据文件
- 将待分析商品图片放入`/my_product_image`
- Excel词表放置于项目根目录

### 运行指令
```bash
# 启动爬虫采集（需保持浏览器可见）
python main.py

# 运行竞品分析 
python competitive_analysis.py
```

---

## 待实现功能
- [ ] 商品相似度计算模块（开发中）
- [ ] 自动化报告生成
- [ ] 代理IP支持
