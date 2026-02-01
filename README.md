# 🤖 AI 新闻聚合助手（增强版）

每日自动抓取全球 AI 领域最新动态，智能评分排序，推送到企业微信。

## ✨ 功能特性

- **📡 RSS 优先策略**：稳定可靠，反爬风险低，特别适合 GitHub Actions
- **🌍 多数据源聚合**：TechCrunch、Wired、MIT Tech Review、Hacker News、arXiv 等 10+ 权威来源
- **🔤 智能翻译**：自动将英文标题和内容翻译为中文
- **⭐ 智能评分**：基于重要性、权威性、传播度、创新性、时效性五维度评分
- **📱 企业微信推送**：每日 Top 10 新闻自动推送

## 📊 数据源

| 来源 | 类型 | 权威性 |
|------|------|--------|
| TechCrunch AI | RSS | ⭐⭐⭐⭐ |
| MIT Technology Review | RSS | ⭐⭐⭐⭐⭐ |
| Wired AI | RSS | ⭐⭐⭐⭐ |
| Ars Technica | RSS | ⭐⭐⭐⭐ |
| Hacker News | API/RSS | ⭐⭐⭐⭐ |
| arXiv AI | RSS | ⭐⭐⭐⭐⭐ |
| Hugging Face Blog | RSS | ⭐⭐⭐⭐ |
| OpenAI Blog | Web | ⭐⭐⭐⭐⭐ |
| Anthropic Blog | Web | ⭐⭐⭐⭐⭐ |
| Google AI Blog | Web | ⭐⭐⭐⭐⭐ |
| DeepMind Blog | Web | ⭐⭐⭐⭐⭐ |
| 机器之心 | Web | ⭐⭐⭐⭐ |
| 36氪 AI | Web | ⭐⭐⭐ |

## 🚀 快速开始

### 方式一：GitHub Actions（推荐）

1. **Fork 本仓库** 或创建新仓库并上传代码

2. **配置 Secrets**：
   - 进入仓库 Settings → Secrets and variables → Actions
   - 添加 `WECOM_WEBHOOK_URL`：您的企业微信机器人 Webhook 地址

3. **手动触发测试**：
   - 进入 Actions 页面
   - 点击 "AI News Daily Collector"
   - 点击 "Run workflow"

4. **自动定时执行**：
   - 每天北京时间上午 9 点自动执行
   - 可在 `.github/workflows/daily_news.yml` 中修改时间

### 方式二：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行采集脚本
python scripts/collect_news.py

# 推送到企业微信（需设置环境变量）
export WECOM_WEBHOOK_URL="your_webhook_url"
python scripts/push_wechat.py
```

## 📁 项目结构

```
ai_news/
├── .github/
│   └── workflows/
│       └── daily_news.yml    # GitHub Actions 工作流
├── scripts/
│   ├── collect_news.py       # 新闻采集主脚本
│   ├── push_wechat.py        # 企业微信推送脚本
│   └── test_collect.py       # 测试脚本
├── output/                   # 输出目录
│   ├── ai_news_daily_*.md    # 每日新闻 Markdown
│   └── ai_news_daily_*_top10.json  # Top 10 JSON
├── logs/                     # 日志目录
├── requirements.txt          # Python 依赖
└── README.md
```

## ⏰ 定时配置

GitHub Actions 使用 UTC 时间，配置示例：

| 北京时间 | UTC 时间 | Cron 表达式 |
|---------|----------|-------------|
| 上午 8 点 | 0:00 | `0 0 * * *` |
| 上午 9 点 | 1:00 | `0 1 * * *` |
| 上午 10 点 | 2:00 | `0 2 * * *` |
| 中午 12 点 | 4:00 | `0 4 * * *` |

修改 `.github/workflows/daily_news.yml` 中的 `cron` 表达式即可。

## 📝 输出示例

### Markdown 格式

```markdown
# AI新闻日报 - 2026-01-31

### 1. OpenAI 发布新一代 GPT-5 模型
原文: OpenAI Releases Next-Generation GPT-5 Model

- **来源**: TechCrunch AI
- **综合评分**: 8.5/10
- **内容摘要**: OpenAI 今日发布了备受期待的 GPT-5 模型...
```

### JSON 格式

```json
{
  "title": "OpenAI 发布新一代 GPT-5 模型",
  "original_title": "OpenAI Releases Next-Generation GPT-5 Model",
  "content": "OpenAI 今日发布了备受期待的 GPT-5 模型...",
  "original_content": "OpenAI today released...",
  "source": "TechCrunch AI",
  "score": {
    "total_score": 8.5,
    "importance": 9,
    "authority": 8,
    "spread": 8,
    "innovation": 9,
    "timeliness": 8
  }
}
```

## 🔧 自定义配置

### 添加新的 RSS 源

编辑 `scripts/collect_news.py`，在 `self.rss_feeds` 中添加：

```python
self.rss_feeds = {
    # 已有的源...
    '新源名称': {
        'url': 'https://example.com/feed.xml',
        'authority': 7  # 权威性评分 1-10
    },
}
```

### 修改评分权重

在 `calculate_score` 方法中调整权重：

```python
weights = {
    'importance': 0.25,   # 重要性
    'authority': 0.2,     # 权威性
    'spread': 0.15,       # 传播度
    'innovation': 0.2,    # 创新性
    'timeliness': 0.2     # 时效性
}
```

## ❓ 常见问题

**Q: GitHub Actions 是否收费？**
A: 个人账户每月 2000 分钟免费额度，本项目每次运行约 3-5 分钟，足够使用。

**Q: 如何查看历史新闻？**
A: 在仓库的 `output/` 目录中可以看到所有历史新闻文件。

**Q: 企业微信没收到消息？**
A: 检查 Secrets 中的 `WECOM_WEBHOOK_URL` 是否正确配置。

## 📄 License

MIT License
