#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻聚合助手 - 新闻采集与分析脚本（增强版）
改进：
1. 添加Twitter/X、Reddit等多平台数据源（参考项目1）
2. 使用Google翻译API进行智能翻译，确保输出统一为中文
3. 优化评分排序逻辑
4. 扩展搜索关键词覆盖范围
5. 【新增】RSS优先抓取策略，提高稳定性，降低反爬风险
"""
import os
import sys
import json
import re
import hashlib
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# 尝试导入翻译库
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
    print("✅ Google翻译API已加载")
except ImportError:
    print("警告：deep-translator未安装，将使用备用词典翻译")
    print("安装命令: pip install deep-translator")
    GoogleTranslator = None
    TRANSLATOR_AVAILABLE = False

# 尝试导入MCP工具（参考项目1的方式）
# 获取脚本所在目录的上级目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(PROJECT_DIR)
try:
    from mcp_matrix import batch_web_search, twitter_search_tweets, extract_content_from_websites
    MCP_AVAILABLE = True
except ImportError:
    print("警告：MCP工具导入失败，将使用备用方案（直接网页抓取）")
    batch_web_search = None
    twitter_search_tweets = None
    extract_content_from_websites = None
    MCP_AVAILABLE = False


class AINewsCollector:
    """AI新闻收集器（增强版 - 参考项目1优化）"""
    
    def __init__(self):
        self.date = datetime.now().strftime('%Y-%m-%d')
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.news_items = []
        
        # 使用相对路径，自动获取项目根目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        self.output_dir = os.path.join(project_dir, 'output')
        self.logs_dir = os.path.join(project_dir, 'logs')
        
        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # 日志文件
        self.log_file = os.path.join(self.logs_dir, f'collect_{datetime.now().strftime("%Y%m%d")}.log')
        
        # HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        })
        
        # 扩展的翻译关键词映射（保留原有 + 新增更多）
        self.translate_map = {
            # 保持原样的品牌名
            'ChatGPT': 'ChatGPT',
            'OpenAI': 'OpenAI',
            'Anthropic': 'Anthropic',
            'Claude': 'Claude',
            'GPT-4': 'GPT-4',
            'GPT-5': 'GPT-5',
            'GPT-4o': 'GPT-4o',
            'Gemini': 'Gemini',
            'Llama': 'Llama',
            'Mistral': 'Mistral',
            'DeepMind': 'DeepMind',
            'Google': 'Google',
            'Microsoft': 'Microsoft',
            'Meta': 'Meta',
            'NVIDIA': 'NVIDIA',
            'AI': 'AI',
            'LLM': 'LLM',
            # 核心概念翻译
            'artificial intelligence': '人工智能',
            'machine learning': '机器学习',
            'deep learning': '深度学习',
            'neural network': '神经网络',
            'large language model': '大语言模型',
            'generative AI': '生成式AI',
            'multimodal': '多模态',
            'reasoning': '推理',
            'agent': '智能体',
            'autonomous': '自主',
            # 动作类词汇
            'breakthrough': '重大突破',
            'launch': '发布',
            'release': '发布',
            'announce': '宣布',
            'unveil': '揭晓',
            'introduce': '推出',
            'deploy': '部署',
            'upgrade': '升级',
            'update': '更新',
            # 商业类词汇
            'partnership': '合作',
            'acquisition': '收购',
            'funding': '融资',
            'investment': '投资',
            'valuation': '估值',
            'IPO': '上市',
            # 政策类词汇
            'regulation': '监管',
            'policy': '政策',
            'legislation': '立法',
            'compliance': '合规',
            'safety': '安全',
            'ethics': '伦理',
            # 程度类词汇
            'major': '重大',
            'significant': '重要',
            'critical': '关键',
            'revolutionary': '革命性',
            'innovative': '创新',
            'first': '首款',
            'new': '新',
            'latest': '最新',
            # 技术类词汇
            'open source': '开源',
            'framework': '框架',
            'model': '模型',
            'architecture': '架构',
            'benchmark': '基准测试',
            'performance': '性能',
            'efficiency': '效率',
            'capability': '能力',
            # 警示类词汇
            'warning': '警告',
            'alert': '警示',
            'concern': '担忧',
            'risk': '风险',
        }
        
        # 更全面的英中翻译词典（用于标题完整翻译）
        self.full_translate_dict = {
            # 常用动词
            'is': '是', 'are': '是', 'was': '是', 'were': '是',
            'has': '有', 'have': '有', 'had': '有',
            'will': '将', 'would': '将会', 'could': '可以', 'can': '能',
            'may': '可能', 'might': '可能',
            'gets': '获得', 'get': '获得', 'got': '获得',
            'says': '表示', 'say': '表示', 'said': '表示',
            'makes': '制作', 'make': '制作', 'made': '制作',
            'takes': '采取', 'take': '采取', 'took': '采取',
            'comes': '来', 'come': '来', 'came': '来',
            'goes': '去', 'go': '去', 'went': '去',
            'shows': '展示', 'show': '展示', 'showed': '展示',
            'uses': '使用', 'use': '使用', 'used': '使用',
            'brings': '带来', 'bring': '带来', 'brought': '带来',
            'becomes': '成为', 'become': '成为', 'became': '成为',
            'launches': '发布', 'launched': '发布',
            'releases': '发布', 'released': '发布',
            'announces': '宣布', 'announced': '宣布',
            'unveils': '揭示', 'unveiled': '揭示',
            'introduces': '推出', 'introduced': '推出',
            'reveals': '揭示', 'revealed': '揭示',
            'reports': '报道', 'reported': '报道',
            'claims': '声称', 'claimed': '声称',
            'confirms': '确认', 'confirmed': '确认',
            'denies': '否认', 'denied': '否认',
            'plans': '计划', 'planned': '计划',
            'aims': '目标', 'aimed': '旨在',
            'wants': '想要', 'wanted': '想要',
            'needs': '需要', 'needed': '需要',
            'builds': '构建', 'build': '构建', 'built': '构建',
            'creates': '创建', 'create': '创建', 'created': '创建',
            'develops': '开发', 'develop': '开发', 'developed': '开发',
            'trains': '训练', 'train': '训练', 'trained': '训练',
            'tests': '测试', 'test': '测试', 'tested': '测试',
            'beats': '击败', 'beat': '击败',
            'wins': '赢得', 'win': '赢得', 'won': '赢得',
            'loses': '失去', 'lose': '失去', 'lost': '失去',
            'improves': '改进', 'improve': '改进', 'improved': '改进',
            'enables': '使能', 'enable': '使能', 'enabled': '使能',
            'allows': '允许', 'allow': '允许', 'allowed': '允许',
            'helps': '帮助', 'help': '帮助', 'helped': '帮助',
            'works': '工作', 'work': '工作', 'worked': '工作',
            'runs': '运行', 'run': '运行', 'ran': '运行',
            'supports': '支持', 'support': '支持', 'supported': '支持',
            'offers': '提供', 'offer': '提供', 'offered': '提供',
            'provides': '提供', 'provide': '提供', 'provided': '提供',
            'adds': '添加', 'add': '添加', 'added': '添加',
            'removes': '移除', 'remove': '移除', 'removed': '移除',
            'changes': '改变', 'change': '改变', 'changed': '改变',
            'replaces': '替换', 'replace': '替换', 'replaced': '替换',
            'expands': '扩展', 'expand': '扩展', 'expanded': '扩展',
            'extends': '扩展', 'extend': '扩展', 'extended': '扩展',
            'accelerates': '加速', 'accelerate': '加速', 'accelerated': '加速',
            'slows': '减缓', 'slow': '减缓', 'slowed': '减缓',
            'starts': '开始', 'start': '开始', 'started': '开始',
            'stops': '停止', 'stop': '停止', 'stopped': '停止',
            'ends': '结束', 'end': '结束', 'ended': '结束',
            'begins': '开始', 'begin': '开始', 'began': '开始',
            'continues': '继续', 'continue': '继续', 'continued': '继续',
            'faces': '面临', 'face': '面临', 'faced': '面临',
            'raises': '提高', 'raise': '提高', 'raised': '提高',
            'cuts': '削减', 'cut': '削减',
            'hits': '达到', 'hit': '达到',
            'reaches': '达到', 'reach': '达到', 'reached': '达到',
            'grows': '增长', 'grow': '增长', 'grew': '增长',
            'falls': '下降', 'fall': '下降', 'fell': '下降',
            'rises': '上升', 'rise': '上升', 'rose': '上升',
            'drops': '下降', 'drop': '下降', 'dropped': '下降',
            'jumps': '跳跃', 'jump': '跳跃', 'jumped': '跳跃',
            'surges': '激增', 'surge': '激增', 'surged': '激增',
            'soars': '飙升', 'soar': '飙升', 'soared': '飙升',
            'plunges': '暴跌', 'plunge': '暴跌', 'plunged': '暴跌',
            'dives': '跳水', 'dive': '跳水', 'dived': '跳水',
            'crashes': '崩溃', 'crash': '崩溃', 'crashed': '崩溃',
            'outperforms': '超越', 'outperform': '超越', 'outperformed': '超越',
            'surpasses': '超越', 'surpass': '超越', 'surpassed': '超越',
            'exceeds': '超过', 'exceed': '超过', 'exceeded': '超过',
            'matches': '匹配', 'match': '匹配', 'matched': '匹配',
            'competes': '竞争', 'compete': '竞争', 'competed': '竞争',
            'challenges': '挑战', 'challenge': '挑战', 'challenged': '挑战',
            'threatens': '威胁', 'threaten': '威胁', 'threatened': '威胁',
            'warns': '警告', 'warn': '警告', 'warned': '警告',
            'predicts': '预测', 'predict': '预测', 'predicted': '预测',
            'expects': '预计', 'expect': '预计', 'expected': '预计',
            'believes': '相信', 'believe': '相信', 'believed': '相信',
            'thinks': '认为', 'think': '认为', 'thought': '认为',
            'knows': '知道', 'know': '知道', 'knew': '知道',
            'sees': '看到', 'see': '看到', 'saw': '看到',
            'finds': '发现', 'find': '发现', 'found': '发现',
            'discovers': '发现', 'discover': '发现', 'discovered': '发现',
            'learns': '学习', 'learn': '学习', 'learned': '学习',
            'teaches': '教', 'teach': '教', 'taught': '教',
            'writes': '写', 'write': '写', 'wrote': '写',
            'reads': '读', 'read': '读',
            'speaks': '说', 'speak': '说', 'spoke': '说',
            'tells': '告诉', 'tell': '告诉', 'told': '告诉',
            'asks': '询问', 'ask': '询问', 'asked': '询问',
            'answers': '回答', 'answer': '回答', 'answered': '回答',
            'explains': '解释', 'explain': '解释', 'explained': '解释',
            'describes': '描述', 'describe': '描述', 'described': '描述',
            'argues': '争论', 'argue': '争论', 'argued': '争论',
            'suggests': '建议', 'suggest': '建议', 'suggested': '建议',
            'recommends': '推荐', 'recommend': '推荐', 'recommended': '推荐',
            'proposes': '提议', 'propose': '提议', 'proposed': '提议',
            'considers': '考虑', 'consider': '考虑', 'considered': '考虑',
            'explores': '探索', 'explore': '探索', 'explored': '探索',
            'investigates': '调查', 'investigate': '调查', 'investigated': '调查',
            'analyzes': '分析', 'analyze': '分析', 'analyzed': '分析',
            'evaluates': '评估', 'evaluate': '评估', 'evaluated': '评估',
            'assesses': '评估', 'assess': '评估', 'assessed': '评估',
            'measures': '测量', 'measure': '测量', 'measured': '测量',
            'compares': '比较', 'compare': '比较', 'compared': '比较',
            'combines': '结合', 'combine': '结合', 'combined': '结合',
            'integrates': '整合', 'integrate': '整合', 'integrated': '整合',
            'merges': '合并', 'merge': '合并', 'merged': '合并',
            'acquires': '收购', 'acquire': '收购', 'acquired': '收购',
            'buys': '购买', 'buy': '购买', 'bought': '购买',
            'sells': '出售', 'sell': '出售', 'sold': '出售',
            'invests': '投资', 'invest': '投资', 'invested': '投资',
            'funds': '资助', 'fund': '资助', 'funded': '资助',
            'partners': '合作', 'partner': '合作', 'partnered': '合作',
            'collaborates': '协作', 'collaborate': '协作', 'collaborated': '协作',
            'joins': '加入', 'join': '加入', 'joined': '加入',
            'leaves': '离开', 'leave': '离开', 'left': '离开',
            'hires': '招聘', 'hire': '招聘', 'hired': '招聘',
            'fires': '解雇', 'fire': '解雇', 'fired': '解雇',
            'appoints': '任命', 'appoint': '任命', 'appointed': '任命',
            'names': '命名', 'name': '命名', 'named': '命名',
            'leads': '领导', 'lead': '领导', 'led': '领导',
            'follows': '跟随', 'follow': '跟随', 'followed': '跟随',
            'copies': '复制', 'copy': '复制', 'copied': '复制',
            'steals': '窃取', 'steal': '窃取', 'stole': '窃取',
            'sues': '起诉', 'sue': '起诉', 'sued': '起诉',
            'bans': '禁止', 'ban': '禁止', 'banned': '禁止',
            'blocks': '阻止', 'block': '阻止', 'blocked': '阻止',
            'limits': '限制', 'limit': '限制', 'limited': '限制',
            'restricts': '限制', 'restrict': '限制', 'restricted': '限制',
            'regulates': '监管', 'regulate': '监管', 'regulated': '监管',
            'controls': '控制', 'control': '控制', 'controlled': '控制',
            'manages': '管理', 'manage': '管理', 'managed': '管理',
            'handles': '处理', 'handle': '处理', 'handled': '处理',
            'solves': '解决', 'solve': '解决', 'solved': '解决',
            'fixes': '修复', 'fix': '修复', 'fixed': '修复',
            'addresses': '解决', 'address': '解决', 'addressed': '解决',
            'tackles': '解决', 'tackle': '解决', 'tackled': '解决',
            'overcomes': '克服', 'overcome': '克服', 'overcame': '克服',
            'achieves': '实现', 'achieve': '实现', 'achieved': '实现',
            'accomplishes': '完成', 'accomplish': '完成', 'accomplished': '完成',
            'completes': '完成', 'complete': '完成', 'completed': '完成',
            'finishes': '完成', 'finish': '完成', 'finished': '完成',
            'delivers': '交付', 'deliver': '交付', 'delivered': '交付',
            'ships': '发布', 'ship': '发布', 'shipped': '发布',
            'rolls': '推出', 'roll': '推出', 'rolled': '推出',
            'pushes': '推动', 'push': '推动', 'pushed': '推动',
            'pulls': '拉', 'pull': '拉', 'pulled': '拉',
            'drives': '驱动', 'drive': '驱动', 'drove': '驱动',
            'powers': '驱动', 'power': '驱动', 'powered': '驱动',
            'fuels': '推动', 'fuel': '推动', 'fueled': '推动',
            'sparks': '引发', 'spark': '引发', 'sparked': '引发',
            'triggers': '触发', 'trigger': '触发', 'triggered': '触发',
            'causes': '导致', 'cause': '导致', 'caused': '导致',
            'leads': '导致', 'lead': '导致', 'led': '导致',
            'results': '导致', 'result': '导致', 'resulted': '导致',
            'produces': '产生', 'produce': '产生', 'produced': '产生',
            'generates': '生成', 'generate': '生成', 'generated': '生成',
            'outputs': '输出', 'output': '输出',
            'inputs': '输入', 'input': '输入',
            'processes': '处理', 'process': '处理', 'processed': '处理',
            'transforms': '转换', 'transform': '转换', 'transformed': '转换',
            'converts': '转换', 'convert': '转换', 'converted': '转换',
            'translates': '翻译', 'translate': '翻译', 'translated': '翻译',
            'adapts': '适应', 'adapt': '适应', 'adapted': '适应',
            'adjusts': '调整', 'adjust': '调整', 'adjusted': '调整',
            'modifies': '修改', 'modify': '修改', 'modified': '修改',
            'customizes': '定制', 'customize': '定制', 'customized': '定制',
            'optimizes': '优化', 'optimize': '优化', 'optimized': '优化',
            'enhances': '增强', 'enhance': '增强', 'enhanced': '增强',
            'boosts': '提升', 'boost': '提升', 'boosted': '提升',
            'strengthens': '加强', 'strengthen': '加强', 'strengthened': '加强',
            'weakens': '削弱', 'weaken': '削弱', 'weakened': '削弱',
            'reduces': '减少', 'reduce': '减少', 'reduced': '减少',
            'decreases': '减少', 'decrease': '减少', 'decreased': '减少',
            'increases': '增加', 'increase': '增加', 'increased': '增加',
            'doubles': '翻倍', 'double': '翻倍', 'doubled': '翻倍',
            'triples': '三倍', 'triple': '三倍', 'tripled': '三倍',
            'halves': '减半', 'halve': '减半', 'halved': '减半',
            'scales': '扩展', 'scale': '扩展', 'scaled': '扩展',
            'shrinks': '缩小', 'shrink': '缩小', 'shrank': '缩小',
            'expands': '扩大', 'expand': '扩大',
            # 常用名词
            'company': '公司', 'companies': '公司',
            'startup': '初创公司', 'startups': '初创公司',
            'firm': '公司', 'firms': '公司',
            'corporation': '企业', 'corporations': '企业',
            'business': '业务', 'businesses': '业务',
            'industry': '行业', 'industries': '行业',
            'market': '市场', 'markets': '市场',
            'sector': '领域', 'sectors': '领域',
            'field': '领域', 'fields': '领域',
            'area': '领域', 'areas': '领域',
            'domain': '领域', 'domains': '领域',
            'technology': '技术', 'technologies': '技术',
            'tech': '科技',
            'tool': '工具', 'tools': '工具',
            'product': '产品', 'products': '产品',
            'service': '服务', 'services': '服务',
            'platform': '平台', 'platforms': '平台',
            'system': '系统', 'systems': '系统',
            'software': '软件',
            'hardware': '硬件',
            'application': '应用', 'applications': '应用',
            'app': '应用', 'apps': '应用',
            'feature': '功能', 'features': '功能',
            'function': '功能', 'functions': '功能',
            'ability': '能力', 'abilities': '能力',
            'skill': '技能', 'skills': '技能',
            'task': '任务', 'tasks': '任务',
            'job': '工作', 'jobs': '工作',
            'role': '角色', 'roles': '角色',
            'user': '用户', 'users': '用户',
            'customer': '客户', 'customers': '客户',
            'developer': '开发者', 'developers': '开发者',
            'researcher': '研究人员', 'researchers': '研究人员',
            'scientist': '科学家', 'scientists': '科学家',
            'engineer': '工程师', 'engineers': '工程师',
            'expert': '专家', 'experts': '专家',
            'leader': '领导者', 'leaders': '领导者',
            'CEO': '首席执行官', 'CTO': '首席技术官', 'CFO': '首席财务官',
            'founder': '创始人', 'founders': '创始人',
            'cofounder': '联合创始人', 'cofounders': '联合创始人',
            'team': '团队', 'teams': '团队',
            'group': '集团', 'groups': '集团',
            'organization': '组织', 'organizations': '组织',
            'government': '政府', 'governments': '政府',
            'agency': '机构', 'agencies': '机构',
            'institution': '机构', 'institutions': '机构',
            'university': '大学', 'universities': '大学',
            'lab': '实验室', 'labs': '实验室',
            'laboratory': '实验室', 'laboratories': '实验室',
            'center': '中心', 'centers': '中心',
            'institute': '研究所', 'institutes': '研究所',
            'research': '研究',
            'study': '研究', 'studies': '研究',
            'paper': '论文', 'papers': '论文',
            'report': '报告', 'reports': '报告',
            'article': '文章', 'articles': '文章',
            'blog': '博客', 'blogs': '博客',
            'post': '帖子', 'posts': '帖子',
            'news': '新闻',
            'announcement': '公告', 'announcements': '公告',
            'statement': '声明', 'statements': '声明',
            'interview': '采访', 'interviews': '采访',
            'speech': '演讲', 'speeches': '演讲',
            'presentation': '演示', 'presentations': '演示',
            'demo': '演示', 'demos': '演示',
            'showcase': '展示', 'showcases': '展示',
            'event': '活动', 'events': '活动',
            'conference': '会议', 'conferences': '会议',
            'summit': '峰会', 'summits': '峰会',
            'meeting': '会议', 'meetings': '会议',
            'deal': '交易', 'deals': '交易',
            'agreement': '协议', 'agreements': '协议',
            'contract': '合同', 'contracts': '合同',
            'license': '许可', 'licenses': '许可',
            'patent': '专利', 'patents': '专利',
            'copyright': '版权', 'copyrights': '版权',
            'lawsuit': '诉讼', 'lawsuits': '诉讼',
            'case': '案例', 'cases': '案例',
            'issue': '问题', 'issues': '问题',
            'problem': '问题', 'problems': '问题',
            'challenge': '挑战', 'challenges': '挑战',
            'opportunity': '机会', 'opportunities': '机会',
            'threat': '威胁', 'threats': '威胁',
            'risk': '风险', 'risks': '风险',
            'danger': '危险', 'dangers': '危险',
            'concern': '担忧', 'concerns': '担忧',
            'worry': '担忧', 'worries': '担忧',
            'fear': '恐惧', 'fears': '恐惧',
            'hope': '希望', 'hopes': '希望',
            'dream': '梦想', 'dreams': '梦想',
            'vision': '愿景', 'visions': '愿景',
            'goal': '目标', 'goals': '目标',
            'target': '目标', 'targets': '目标',
            'objective': '目标', 'objectives': '目标',
            'plan': '计划', 'plans': '计划',
            'strategy': '战略', 'strategies': '战略',
            'approach': '方法', 'approaches': '方法',
            'method': '方法', 'methods': '方法',
            'technique': '技术', 'techniques': '技术',
            'solution': '解决方案', 'solutions': '解决方案',
            'answer': '答案', 'answers': '答案',
            'response': '回应', 'responses': '回应',
            'reaction': '反应', 'reactions': '反应',
            'feedback': '反馈',
            'review': '评测', 'reviews': '评测',
            'rating': '评分', 'ratings': '评分',
            'score': '得分', 'scores': '得分',
            'result': '结果', 'results': '结果',
            'outcome': '结果', 'outcomes': '结果',
            'effect': '效果', 'effects': '效果',
            'impact': '影响', 'impacts': '影响',
            'influence': '影响', 'influences': '影响',
            'change': '变化', 'changes': '变化',
            'shift': '转变', 'shifts': '转变',
            'transition': '过渡', 'transitions': '过渡',
            'transformation': '转型', 'transformations': '转型',
            'revolution': '革命', 'revolutions': '革命',
            'evolution': '进化', 'evolutions': '进化',
            'progress': '进展',
            'advance': '进展', 'advances': '进展',
            'advancement': '进步', 'advancements': '进步',
            'development': '发展', 'developments': '发展',
            'growth': '增长',
            'expansion': '扩张', 'expansions': '扩张',
            'trend': '趋势', 'trends': '趋势',
            'pattern': '模式', 'patterns': '模式',
            'cycle': '周期', 'cycles': '周期',
            'phase': '阶段', 'phases': '阶段',
            'stage': '阶段', 'stages': '阶段',
            'step': '步骤', 'steps': '步骤',
            'level': '级别', 'levels': '级别',
            'tier': '层', 'tiers': '层',
            'layer': '层', 'layers': '层',
            'version': '版本', 'versions': '版本',
            'edition': '版本', 'editions': '版本',
            'generation': '代', 'generations': '代',
            'era': '时代', 'eras': '时代',
            'age': '时代', 'ages': '时代',
            'future': '未来', 'futures': '未来',
            'past': '过去',
            'present': '现在',
            'today': '今天',
            'tomorrow': '明天',
            'yesterday': '昨天',
            'year': '年', 'years': '年',
            'month': '月', 'months': '月',
            'week': '周', 'weeks': '周',
            'day': '天', 'days': '天',
            'hour': '小时', 'hours': '小时',
            'minute': '分钟', 'minutes': '分钟',
            'second': '秒', 'seconds': '秒',
            'time': '时间', 'times': '时间',
            'world': '世界', 'worlds': '世界',
            'global': '全球',
            'international': '国际',
            'national': '国家',
            'local': '本地',
            'regional': '区域',
            'country': '国家', 'countries': '国家',
            'nation': '国家', 'nations': '国家',
            'state': '州', 'states': '州',
            'city': '城市', 'cities': '城市',
            'region': '地区', 'regions': '地区',
            'billion': '十亿',
            'million': '百万',
            'thousand': '千',
            'hundred': '百',
            'percent': '百分比',
            'dollar': '美元', 'dollars': '美元',
            'price': '价格', 'prices': '价格',
            'cost': '成本', 'costs': '成本',
            'value': '价值', 'values': '价值',
            'worth': '价值',
            'revenue': '收入', 'revenues': '收入',
            'profit': '利润', 'profits': '利润',
            'loss': '损失', 'losses': '损失',
            'gain': '收益', 'gains': '收益',
            'return': '回报', 'returns': '回报',
            'income': '收入', 'incomes': '收入',
            'money': '资金',
            'cash': '现金',
            'capital': '资本',
            'asset': '资产', 'assets': '资产',
            'debt': '债务', 'debts': '债务',
            'stock': '股票', 'stocks': '股票',
            'share': '股份', 'shares': '股份',
            'bond': '债券', 'bonds': '债券',
            'fund': '基金', 'funds': '基金',
            'round': '轮', 'rounds': '轮',
            'series': '系列',
            'seed': '种子',
            # AI相关专业术语
            'chatbot': '聊天机器人', 'chatbots': '聊天机器人',
            'bot': '机器人', 'bots': '机器人',
            'robot': '机器人', 'robots': '机器人',
            'robotics': '机器人技术',
            'automation': '自动化',
            'algorithm': '算法', 'algorithms': '算法',
            'data': '数据',
            'dataset': '数据集', 'datasets': '数据集',
            'database': '数据库', 'databases': '数据库',
            'training': '训练',
            'inference': '推理',
            'prediction': '预测', 'predictions': '预测',
            'classification': '分类',
            'recognition': '识别',
            'detection': '检测',
            'generation': '生成',
            'synthesis': '合成',
            'analysis': '分析',
            'processing': '处理',
            'understanding': '理解',
            'learning': '学习',
            'intelligence': '智能',
            'cognition': '认知',
            'perception': '感知',
            'vision': '视觉',
            'speech': '语音',
            'language': '语言', 'languages': '语言',
            'text': '文本', 'texts': '文本',
            'image': '图像', 'images': '图像',
            'video': '视频', 'videos': '视频',
            'audio': '音频', 'audios': '音频',
            'voice': '语音', 'voices': '语音',
            'sound': '声音', 'sounds': '声音',
            'code': '代码', 'codes': '代码',
            'coding': '编程',
            'programming': '编程',
            'prompt': '提示词', 'prompts': '提示词',
            'token': '令牌', 'tokens': '令牌',
            'parameter': '参数', 'parameters': '参数',
            'weight': '权重', 'weights': '权重',
            'layer': '层', 'layers': '层',
            'neuron': '神经元', 'neurons': '神经元',
            'attention': '注意力',
            'transformer': 'Transformer',
            'encoder': '编码器', 'encoders': '编码器',
            'decoder': '解码器', 'decoders': '解码器',
            'embedding': '嵌入', 'embeddings': '嵌入',
            'vector': '向量', 'vectors': '向量',
            'matrix': '矩阵', 'matrices': '矩阵',
            'tensor': '张量', 'tensors': '张量',
            'GPU': 'GPU', 'GPUs': 'GPU',
            'CPU': 'CPU', 'CPUs': 'CPU',
            'chip': '芯片', 'chips': '芯片',
            'processor': '处理器', 'processors': '处理器',
            'server': '服务器', 'servers': '服务器',
            'cloud': '云',
            'edge': '边缘',
            'device': '设备', 'devices': '设备',
            'computer': '计算机', 'computers': '计算机',
            'computing': '计算',
            'memory': '内存',
            'storage': '存储',
            'bandwidth': '带宽',
            'latency': '延迟',
            'throughput': '吞吐量',
            'speed': '速度',
            'accuracy': '准确率',
            'precision': '精度',
            'recall': '召回率',
            'loss': '损失',
            'error': '误差', 'errors': '误差',
            'bias': '偏见', 'biases': '偏见',
            'fairness': '公平性',
            'transparency': '透明度',
            'explainability': '可解释性',
            'interpretability': '可解释性',
            'alignment': '对齐',
            'safety': '安全',
            'security': '安全性',
            'privacy': '隐私',
            'trust': '信任',
            'reliability': '可靠性',
            'robustness': '鲁棒性',
            'scalability': '可扩展性',
            'efficiency': '效率',
            'effectiveness': '有效性',
            'quality': '质量',
            'quantity': '数量',
            'size': '大小', 'sizes': '大小',
            'scale': '规模', 'scales': '规模',
            'scope': '范围', 'scopes': '范围',
            'range': '范围', 'ranges': '范围',
            'limit': '限制', 'limits': '限制',
            'boundary': '边界', 'boundaries': '边界',
            'frontier': '前沿', 'frontiers': '前沿',
            'edge': '边缘', 'edges': '边缘',
            'core': '核心', 'cores': '核心',
            'base': '基础', 'bases': '基础',
            'foundation': '基础', 'foundations': '基础',
            'fundamental': '基本',
            'basic': '基本',
            'advanced': '高级',
            'sophisticated': '复杂',
            'complex': '复杂',
            'simple': '简单',
            'easy': '简单',
            'difficult': '困难',
            'hard': '困难',
            'challenging': '具有挑战性',
            'impossible': '不可能',
            'possible': '可能',
            'likely': '可能',
            'unlikely': '不太可能',
            'certain': '确定',
            'uncertain': '不确定',
            'clear': '清楚',
            'unclear': '不清楚',
            'obvious': '明显',
            'subtle': '微妙',
            'significant': '重大',
            'important': '重要',
            'critical': '关键',
            'essential': '必要',
            'necessary': '必要',
            'optional': '可选',
            'required': '必需',
            'mandatory': '强制',
            'voluntary': '自愿',
            'free': '免费',
            'paid': '付费',
            'premium': '高级',
            'standard': '标准',
            'custom': '自定义',
            'default': '默认',
            'official': '官方',
            'unofficial': '非官方',
            'public': '公开',
            'private': '私有',
            'open': '开放',
            'closed': '封闭',
            'available': '可用',
            'unavailable': '不可用',
            'online': '在线',
            'offline': '离线',
            'live': '实时',
            'real-time': '实时',
            'instant': '即时',
            'fast': '快速',
            'slow': '缓慢',
            'quick': '快速',
            'rapid': '快速',
            'immediate': '立即',
            'soon': '即将',
            'next': '下一个',
            'previous': '上一个',
            'current': '当前',
            'former': '前',
            'latter': '后者',
            'first': '首个',
            'last': '最后',
            'final': '最终',
            'initial': '初始',
            'original': '原始',
            'updated': '更新的',
            'improved': '改进的',
            'enhanced': '增强的',
            'upgraded': '升级的',
            'new': '新的',
            'old': '旧的',
            'modern': '现代',
            'traditional': '传统',
            'classic': '经典',
            'novel': '新颖',
            'unique': '独特',
            'special': '特殊',
            'general': '通用',
            'specific': '特定',
            'particular': '特定',
            'individual': '个人',
            'personal': '个人',
            'professional': '专业',
            'commercial': '商业',
            'enterprise': '企业',
            'consumer': '消费者',
            'retail': '零售',
            'wholesale': '批发',
            'domestic': '国内',
            'foreign': '外国',
            'overseas': '海外',
            'worldwide': '全球',
            # 常用介词和连词
            'the': '', 'a': '', 'an': '',
            'of': '的', 'for': '为', 'to': '到', 'from': '从',
            'in': '在', 'on': '在', 'at': '在',
            'by': '由', 'with': '与', 'without': '没有',
            'about': '关于', 'around': '约', 'between': '之间',
            'through': '通过', 'during': '期间', 'before': '之前', 'after': '之后',
            'above': '以上', 'below': '以下', 'under': '下',
            'over': '超过', 'into': '进入', 'out': '出',
            'up': '上', 'down': '下',
            'and': '和', 'or': '或', 'but': '但',
            'if': '如果', 'then': '那么', 'else': '否则',
            'when': '当', 'where': '哪里', 'why': '为什么', 'how': '如何',
            'what': '什么', 'which': '哪个', 'who': '谁', 'whom': '谁',
            'that': '那个', 'this': '这个', 'these': '这些', 'those': '那些',
            'all': '所有', 'some': '一些', 'any': '任何', 'no': '没有',
            'every': '每个', 'each': '每个', 'both': '两者', 'either': '任一',
            'neither': '两者都不', 'none': '没有',
            'more': '更多', 'less': '更少', 'most': '最', 'least': '最少',
            'much': '很多', 'many': '很多', 'few': '很少', 'little': '很少',
            'very': '非常', 'too': '太', 'so': '如此', 'such': '如此',
            'quite': '相当', 'rather': '相当', 'fairly': '相当',
            'really': '真的', 'actually': '实际上', 'basically': '基本上',
            'especially': '特别是', 'particularly': '特别是',
            'mainly': '主要', 'mostly': '主要', 'largely': '大部分',
            'entirely': '完全', 'completely': '完全', 'totally': '完全',
            'fully': '完全', 'partly': '部分', 'partially': '部分',
            'almost': '几乎', 'nearly': '几乎', 'just': '刚刚',
            'only': '只', 'even': '甚至', 'still': '仍然', 'yet': '还',
            'already': '已经', 'now': '现在', 'then': '然后',
            'here': '这里', 'there': '那里', 'everywhere': '到处',
            'somewhere': '某处', 'nowhere': '无处', 'anywhere': '任何地方',
            'also': '也', 'again': '再次', 'always': '总是', 'never': '从不',
            'often': '经常', 'sometimes': '有时', 'usually': '通常',
            'rarely': '很少', 'seldom': '很少',
            'perhaps': '也许', 'maybe': '也许', 'probably': '可能',
            'certainly': '当然', 'definitely': '肯定', 'surely': '肯定',
            'however': '然而', 'therefore': '因此', 'thus': '因此',
            'hence': '因此', 'meanwhile': '同时', 'furthermore': '此外',
            'moreover': '而且', 'besides': '此外', 'otherwise': '否则',
            'instead': '而是', 'rather': '宁愿', 'despite': '尽管',
            'although': '虽然', 'though': '尽管', 'while': '当', 'whereas': '然而',
            'unless': '除非', 'until': '直到', 'since': '自从', 'because': '因为',
            'as': '作为', 'like': '像', 'unlike': '不像',
            'according': '根据', 'regarding': '关于', 'concerning': '关于',
            'including': '包括', 'excluding': '不包括',
            'following': '以下', 'considering': '考虑到',
            # 补充遗漏的常用词
            'course': '路线', 'courses': '路线',
            'charts': '规划', 'chart': '规划', 'charted': '规划',
            'flagship': '旗舰',
            'sales': '销售',
            'momentum': '势头',
            'propel': '推动', 'propels': '推动', 'propelled': '推动',
            'ambitions': '雄心', 'ambition': '雄心',
            'seeks': '寻求', 'seek': '寻求', 'sought': '寻求',
            'federal': '联邦',
            'approval': '批准', 'approvals': '批准',
            'solar': '太阳能',
            'powered': '驱动的',
            'satellite': '卫星', 'satellites': '卫星',
            'data center': '数据中心', 'data centers': '数据中心',
            'weather': '天气',
            'forecast': '预测', 'forecasts': '预测', 'forecasting': '预测',
            'faster': '更快',
            'cheaper': '更便宜',
            'red': '红', 'blue': '蓝',
            'team': '团队', 'teams': '团队',
            'test': '测试', 'tests': '测试', 'tested': '测试',
            'ran': '运行',
            'AMA': '问答',
            'our': '我们的',
            'their': '他们的',
            'its': '它的',
            'your': '你的',
            'my': '我的',
            'his': '他的',
            'her': '她的',
            'rumored': '传闻', 'rumor': '传闻', 'rumors': '传闻',
            'merger': '合并', 'mergers': '合并',
            'apparent': '明显',
            'confirmation': '确认',
            'selects': '选择', 'select': '选择', 'selected': '选择',
            'build': '构建', 'builds': '构建', 'built': '构建',
            'design': '设计', 'designs': '设计', 'designed': '设计',
            'using': '使用',
            'eight': '八',
            'billion': '十亿',
            'parameter': '参数', 'parameters': '参数',
            'state': '状态', 'states': '状态',
            'space': '空间', 'spaces': '空间',
            'complaints': '投诉', 'complaint': '投诉',
            'megathread': '讨论帖',
            'vs': '对抗',
            'brewery': '酿酒厂',
            'beverage': '饮料',
            'inbox': '收件箱',
            'feel': '感觉',
            'fraction': '一小部分',
            'cost': '成本', 'costs': '成本',
            'demonstrating': '展示',
            'viability': '可行性',
            'next-generation': '下一代',
            # 更多遗漏词汇
            'models': '模型',
            'we': '我们',
            'they': '他们',
            'it': '它',
            'he': '他',
            'she': '她',
            'I': '我',
            'you': '你',
            'me': '我',
            'him': '他',
            'us': '我们',
            'them': '他们',
            'agents': '智能体',
            'live': '实时',
            'real': '真实',
            'time': '时间',
        }
        
        # === RSS Feed 配置（优先使用，稳定性高，反爬风险低）===
        # 特别适合 GitHub Actions 环境
        self.rss_feeds = {
            # === 一级权威来源（AI公司官方、顶级科技媒体）===
            'TechCrunch AI': {
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'authority': 8,
                'category': 'tech_media'
            },
            'Wired AI': {
                'url': 'https://www.wired.com/feed/tag/ai/latest/rss',
                'authority': 8,
                'category': 'tech_media'
            },
            'MIT Technology Review': {
                'url': 'https://www.technologyreview.com/feed/',
                'authority': 9,
                'category': 'tech_media'
            },
            'Ars Technica': {
                'url': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
                'authority': 7,
                'category': 'tech_media'
            },
            
            # === Hacker News（硅谷风向标）===
            'Hacker News Front Page': {
                'url': 'https://hnrss.org/frontpage',
                'authority': 7,
                'category': 'community'
            },
            'Hacker News Best': {
                'url': 'https://hnrss.org/best',
                'authority': 7,
                'category': 'community'
            },
            
            # === 学术来源 ===
            'arXiv AI': {
                'url': 'https://export.arxiv.org/rss/cs.AI',
                'authority': 9,
                'category': 'academic'
            },
            'arXiv Machine Learning': {
                'url': 'https://export.arxiv.org/rss/cs.LG',
                'authority': 9,
                'category': 'academic'
            },
            
            # === AI专业媒体 ===
            'The Gradient': {
                'url': 'https://thegradient.pub/rss/',
                'authority': 8,
                'category': 'ai_media'
            },
            
            # === 开发者社区 ===
            'Hugging Face Blog': {
                'url': 'https://huggingface.co/blog/feed.xml',
                'authority': 8,
                'category': 'ai_company'
            },
        }
    
    def log(self, message, level='INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg)
        
        print(log_msg.strip())
    
    def fetch_rss_feeds(self):
        """
        【核心方法】从所有配置的RSS源获取新闻
        优势：
        1. 稳定性高 - RSS是标准格式，解析简单可靠
        2. 反爬风险低 - 不直接访问原网站HTML
        3. 数据结构化 - XML格式，解析比HTML简单100倍
        特别适合 GitHub Actions 环境
        """
        results = []
        self.log("🚀 RSS优先抓取策略启动...")
        
        # AI相关关键词，用于筛选非AI专题RSS中的相关内容
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'chatgpt', 'gpt', 'llm', 'openai', 'anthropic', 'claude', 'gemini',
            'llama', 'neural', 'transformer', 'model', 'training', 'inference',
            'agent', 'rag', 'embedding', 'diffusion', 'stable diffusion', 'midjourney',
            'copilot', 'generative', 'nlp', 'computer vision', 'robotics',
            '人工智能', '机器学习', '深度学习', '大模型', '智能体'
        ]
        
        def is_ai_related(title, description=''):
            """检查新闻是否与AI相关"""
            text = (title + ' ' + description).lower()
            return any(kw in text for kw in ai_keywords)
        
        def parse_rss_item(item, source_name, authority, namespaces=None):
            """解析单个RSS条目"""
            # 尝试获取标题
            title = ''
            title_elem = item.find('title')
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
                # 处理CDATA
                if title.startswith('<![CDATA['):
                    title = title.replace('<![CDATA[', '').replace(']]>', '')
            
            if not title or len(title) < 10:
                return None
            
            # 尝试获取链接
            link = ''
            link_elem = item.find('link')
            if link_elem is not None:
                link = link_elem.text.strip() if link_elem.text else ''
                if not link:
                    link = link_elem.get('href', '')
            
            if not link:
                guid_elem = item.find('guid')
                if guid_elem is not None and guid_elem.text:
                    if guid_elem.text.startswith('http'):
                        link = guid_elem.text.strip()
            
            if not link or not link.startswith('http'):
                return None
            
            # 尝试获取描述/内容
            description = ''
            for desc_tag in ['description', 'summary', 'content']:
                desc_elem = item.find(desc_tag)
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text.strip()
                    # 移除HTML标签
                    description = re.sub(r'<[^>]+>', '', description)
                    description = description[:300]
                    break
            
            # 尝试获取发布时间
            pub_date = self.yesterday
            for date_tag in ['pubDate', 'published', 'updated', 'dc:date']:
                date_elem = item.find(date_tag)
                if date_elem is not None and date_elem.text:
                    pub_date = date_elem.text.strip()[:10]
                    break
            
            return {
                'title': title,
                'url': link,
                'content': description,
                'publish_time': pub_date,
                'source': source_name,
                'authority_score': authority
            }
        
        # 并行获取所有RSS源
        def fetch_single_rss(name, config):
            """获取单个RSS源"""
            feed_results = []
            try:
                response = self.session.get(config['url'], timeout=15)
                if response.status_code != 200:
                    return feed_results
                
                # 解析XML
                try:
                    # 尝试用ElementTree解析
                    root = ET.fromstring(response.content)
                    
                    # 查找所有item或entry（支持RSS和Atom格式）
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    
                    for item in items[:15]:  # 每源最多15条
                        parsed = parse_rss_item(item, name, config['authority'])
                        if parsed:
                            # 对于非AI专题源，需要筛选AI相关内容
                            if config['category'] in ['ai_media', 'ai_company', 'academic']:
                                feed_results.append(parsed)
                            elif is_ai_related(parsed['title'], parsed['content']):
                                feed_results.append(parsed)
                                
                except ET.ParseError:
                    # ElementTree解析失败，使用BeautifulSoup
                    soup = BeautifulSoup(response.content, 'html.parser')
                    items = soup.find_all('item') or soup.find_all('entry')
                    
                    for item in items[:15]:
                        title_elem = item.find('title')
                        link_elem = item.find('link')
                        desc_elem = item.find('description') or item.find('summary')
                        
                        title = title_elem.get_text(strip=True) if title_elem else ''
                        link = ''
                        if link_elem:
                            link = link_elem.get_text(strip=True) or link_elem.get('href', '')
                        desc = desc_elem.get_text(strip=True)[:300] if desc_elem else ''
                        
                        if title and link and len(title) >= 10:
                            if config['category'] in ['ai_media', 'ai_company', 'academic']:
                                feed_results.append({
                                    'title': title,
                                    'url': link,
                                    'content': desc,
                                    'publish_time': self.yesterday,
                                    'source': name,
                                    'authority_score': config['authority']
                                })
                            elif is_ai_related(title, desc):
                                feed_results.append({
                                    'title': title,
                                    'url': link,
                                    'content': desc,
                                    'publish_time': self.yesterday,
                                    'source': name,
                                    'authority_score': config['authority']
                                })
                
            except Exception as e:
                self.log(f"RSS源 {name} 获取失败: {e}", 'WARNING')
            
            return feed_results
        
        # 并行获取所有RSS源
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_single_rss, name, config): name 
                for name, config in self.rss_feeds.items()
            }
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    feed_results = future.result()
                    if feed_results:
                        results.extend(feed_results)
                        self.log(f"  ✓ {source_name}: {len(feed_results)} 条")
                except Exception as e:
                    self.log(f"  ✗ {source_name}: 失败 - {e}", 'WARNING')
        
        self.log(f"📰 RSS抓取完成，共获取 {len(results)} 条新闻")
        return results
    
    def google_translate(self, text, max_retries=3):
        """
        使用Google翻译API进行翻译（免费方案）
        使用deep-translator库调用Google翻译
        """
        if not text or not text.strip():
            return text
        
        # 如果文本已经主要是中文，直接返回
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s', '', text))
        if total_chars > 0 and chinese_chars / total_chars > 0.6:
            return text
        
        if not TRANSLATOR_AVAILABLE:
            # 回退到词典翻译
            return self.dict_translate(text)
        
        # 使用Google翻译API
        for attempt in range(max_retries):
            try:
                translator = GoogleTranslator(source='auto', target='zh-CN')
                translated = translator.translate(text)
                
                if translated:
                    return translated
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # 递增延迟
                    continue
                else:
                    self.log(f"Google翻译失败，回退到词典翻译: {e}", 'WARNING')
        
        # 所有重试失败，回退到词典翻译
        return self.dict_translate(text)
    
    def dict_translate(self, text):
        """词典翻译（备用方案）"""
        if not text:
            return text
        
        result = text
        
        # 合并两个词典
        combined_dict = {**self.translate_map, **self.full_translate_dict}
        
        # 按照词组长度降序排列，确保长词组优先匹配
        sorted_items = sorted(combined_dict.items(), key=lambda x: len(x[0]), reverse=True)
        
        for eng, chn in sorted_items:
            if not eng:  # 跳过空键
                continue
            # 使用单词边界匹配
            pattern = r'\b' + re.escape(eng) + r'\b'
            result = re.sub(pattern, chn, result, flags=re.IGNORECASE)
        
        # 清理多余的空格和标点
        result = re.sub(r'\s+', ' ', result).strip()
        result = re.sub(r'\s*([,，.。:：;；!！?？])\s*', r'\1', result)
        
        return result
    
    def simple_translate(self, text):
        """简单的关键词翻译（增强版）- 保留用于内容摘要"""
        if not text:
            return text
        
        result = text
        # 按照词组长度降序排列，确保长词组优先匹配
        sorted_items = sorted(self.translate_map.items(), key=lambda x: len(x[0]), reverse=True)
        for eng, chn in sorted_items:
            # 使用更精确的匹配
            pattern = r'\b' + re.escape(eng) + r'\b'
            result = re.sub(pattern, chn, result, flags=re.IGNORECASE)
        
        return result
    
    def translate_title(self, title):
        """
        翻译标题为中文（使用Google翻译API）
        """
        if not title or not title.strip():
            return title
        
        # 如果文本已经主要是中文，直接返回
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', title))
        total_chars = len(re.sub(r'\s', '', title))
        if total_chars > 0 and chinese_chars / total_chars > 0.6:
            return title
        
        # 使用Google翻译
        return self.google_translate(title)
    
    def is_valid_url(self, url):
        """验证URL是否有效"""
        if not url:
            return False
        url = url.strip()
        return url.startswith('http://') or url.startswith('https://') and len(url) > 20
    
    def clean_content(self, content):
        """清理内容，移除HTML标签和特殊字符"""
        if not content:
            return ""
        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        # 移除特殊字符，保留中文、英文、数字和常用标点
        content = re.sub(r'[^\w\s\u4e00-\u9fff.,!?\'"-]', '', content)
        # 移除多余空白
        content = re.sub(r'\s+', ' ', content).strip()
        return content[:300]  # 限制长度
    
    def search_news_from_web(self, queries):
        """从搜索引擎获取新闻（增强版：优先使用MCP工具，回退到直接抓取）"""
        
        # === 优先使用MCP工具（参考项目1） ===
        if MCP_AVAILABLE and batch_web_search:
            try:
                self.log("使用MCP batch_web_search工具获取新闻...")
                search_tasks = []
                for query in queries:
                    search_tasks.append({
                        'query': f"{query} {self.yesterday}",
                        'num_results': 10,
                        'data_range': 'd',
                        'cursor': 1
                    })
                
                results = batch_web_search(
                    queries=search_tasks,
                    display_text=f"搜索{self.yesterday}的AI新闻",
                    search_type='news'
                )
                
                if results:
                    processed_results = []
                    for item in results:
                        if isinstance(item, dict) and 'title' in item:
                            processed_results.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', item.get('link', '')),
                                'content': item.get('snippet', item.get('description', '')),
                                'publish_time': item.get('date', self.yesterday),
                                'source': item.get('source', 'Web Search')
                            })
                    
                    if processed_results:
                        self.log(f"MCP工具获取 {len(processed_results)} 条新闻")
                        return processed_results
                        
            except Exception as e:
                self.log(f"MCP工具搜索出错，回退到直接抓取: {e}", 'WARNING')
        
        # === 回退方案：直接抓取AI新闻源 ===
        try:
            results = []
            
            # 扩展的AI新闻源列表
            ai_news_sources = [
                {
                    'name': 'TechCrunch AI',
                    'url': 'https://techcrunch.com/category/artificial-intelligence/',
                    'selector': 'article',
                    'title_tag': 'h2',
                    'title_class': 'loop-card__title',
                    'link_selector': 'a.loop-card__link',
                    'content_selector': '.loop-card__summary'
                },
                {
                    'name': 'The Verge AI',
                    'url': 'https://www.theverge.com/ai-artificial-intelligence',
                    'selector': 'div',
                    'title_class': 'font-bold',
                    'link_selector': 'a[href*="/2026/"]',
                    'content_selector': ''
                },
                {
                    'name': 'Wired AI',
                    'url': 'https://www.wired.com/tag/artificial-intelligence/',
                    'selector': 'div',
                    'title_tag': 'h3',
                    'link_selector': 'a.summary-item__link',
                    'content_selector': '.summary-item__dek'
                },
                # 新增更多数据源
                {
                    'name': 'Ars Technica AI',
                    'url': 'https://arstechnica.com/ai/',
                    'selector': 'article',
                    'title_tag': 'h2',
                    'link_selector': 'a[href*="/2026/"]',
                    'content_selector': 'p.excerpt'
                },
                {
                    'name': 'VentureBeat AI',
                    'url': 'https://venturebeat.com/category/ai/',
                    'selector': 'article',
                    'title_tag': 'h2',
                    'link_selector': 'a.article-title',
                    'content_selector': '.article-excerpt'
                }
            ]
            
            for source in ai_news_sources:
                try:
                    response = self.session.get(source['url'], timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找文章链接
                        links = soup.select(source['link_selector'])
                        seen_urls = set()
                        
                        for link_elem in links[:8]:  # 每站最多8条
                            url = link_elem.get('href', '').strip()
                            
                            if not url:
                                continue
                            
                            # 补全相对链接
                            if not url.startswith('http'):
                                from urllib.parse import urljoin
                                url = urljoin(source['url'], url)
                            
                            # 去重
                            if url in seen_urls:
                                continue
                            seen_urls.add(url)
                            
                            # 获取标题
                            title = ""
                            if source.get('title_tag') and source.get('title_class'):
                                # 尝试通过父元素查找
                                parent = link_elem.find_parent()
                                if parent:
                                    title_elem = parent.find(source['title_tag'], class_=source.get('title_class').replace(' ', '.'))
                                    if title_elem:
                                        title = title_elem.get_text(strip=True)
                            
                            if not title:
                                title = link_elem.get_text(strip=True)
                            
                            if not title or len(title) < 10:
                                continue
                            
                            results.append({
                                'title': title,
                                'url': url,
                                'content': '',
                                'publish_time': self.yesterday,
                                'source': source['name']
                            })
                            
                except Exception as e:
                    self.log(f"抓取 {source['name']} 出错: {e}", 'WARNING')
                    continue
            
            # 如果直接抓取失败，回退使用Bing RSS
            if len(results) < 5:
                self.log("直接抓取结果不足，尝试Bing RSS...", 'INFO')
                fallback_results = self.search_from_bing_rss(queries)
                results.extend(fallback_results)
            
            self.log(f"网络搜索获取 {len(results)} 条新闻")
            return results
            
        except Exception as e:
            self.log(f"网络搜索出错: {e}", 'ERROR')
            return []
    
    def search_from_twitter(self, keywords):
        """从Twitter/X获取AI相关新闻（增强版：MCP优先，回退到Nitter镜像）"""
        
        # === 方案1：优先使用MCP工具（参考项目1） ===
        if MCP_AVAILABLE and twitter_search_tweets:
            try:
                all_tweets = []
                for keyword in keywords[:5]:  # 限制搜索数量
                    tweets = twitter_search_tweets(
                        query=keyword,
                        start_date=self.yesterday,
                        end_date=self.yesterday,
                        lang='en',
                        limit=20,
                        min_likes=5,
                        display_text=f"搜索Twitter上的{self.yesterday}AI新闻"
                    )
                    if tweets:
                        all_tweets.extend(tweets)
                
                if all_tweets:
                    self.log(f"MCP Twitter工具获取 {len(all_tweets)} 条推文")
                    return all_tweets
            except Exception as e:
                self.log(f"MCP Twitter搜索出错，回退到Nitter: {e}", 'WARNING')
        
        # === 方案2：使用Nitter镜像（不依赖MCP） ===
        self.log("使用Nitter镜像抓取Twitter数据...")
        return self._search_twitter_via_nitter(keywords)
    
    def _search_twitter_via_nitter(self, keywords):
        """通过Nitter镜像抓取Twitter数据（备用方案）"""
        results = []
        
        # Nitter镜像站点列表（多个备用）
        nitter_instances = [
            'https://nitter.poast.org',
            'https://nitter.privacydev.net',
            'https://nitter.woodland.cafe',
            'https://nitter.esmailelbob.xyz',
            'https://nitter.1d4.us',
        ]
        
        # AI领域知名账号（直接抓取其时间线）
        ai_accounts = [
            'OpenAI',
            'AnthropicAI', 
            'GoogleAI',
            'DeepMind',
            'nvidia',
            'huaborface',
            'ylecun',
            'kaborepat',
            'sama',
            'DrJimFan',
            'EMostaque',
        ]
        
        # 搜索关键词（简化版）
        search_queries = [
            'AI%20breakthrough',
            'ChatGPT',
            'Claude%20AI',
            'GPT-4',
            'LLM',
        ]
        
        working_instance = None
        
        # 找到一个可用的Nitter实例
        for instance in nitter_instances:
            try:
                test_url = f"{instance}/OpenAI"
                response = self.session.get(test_url, timeout=10)
                if response.status_code == 200:
                    working_instance = instance
                    self.log(f"使用Nitter实例: {instance}")
                    break
            except Exception:
                continue
        
        if not working_instance:
            self.log("所有Nitter实例不可用，尝试使用Twitter RSS备用方案", 'WARNING')
            return self._search_twitter_via_rss(keywords)
        
        # 方法1：抓取AI领域知名账号的时间线
        for account in ai_accounts[:8]:  # 限制数量
            try:
                url = f"{working_instance}/{account}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找推文
                    tweets = soup.select('.timeline-item')
                    
                    for tweet in tweets[:5]:  # 每个账号最多5条
                        # 提取推文内容
                        content_elem = tweet.select_one('.tweet-content')
                        if not content_elem:
                            continue
                        
                        text = content_elem.get_text(strip=True)
                        if len(text) < 20:
                            continue
                        
                        # 提取链接
                        link_elem = tweet.select_one('.tweet-link')
                        tweet_url = ""
                        if link_elem:
                            href = link_elem.get('href', '')
                            if href:
                                tweet_url = f"https://twitter.com{href}" if href.startswith('/') else href
                        
                        # 提取时间
                        time_elem = tweet.select_one('.tweet-date a')
                        post_time = self.yesterday
                        if time_elem:
                            time_title = time_elem.get('title', '')
                            if time_title:
                                post_time = time_title
                        
                        # 提取互动数据
                        stats = tweet.select('.tweet-stat')
                        likes = 0
                        retweets = 0
                        for stat in stats:
                            stat_text = stat.get_text(strip=True)
                            if 'like' in stat_text.lower():
                                try:
                                    likes = int(''.join(filter(str.isdigit, stat_text)) or 0)
                                except ValueError:
                                    pass
                            elif 'retweet' in stat_text.lower():
                                try:
                                    retweets = int(''.join(filter(str.isdigit, stat_text)) or 0)
                                except ValueError:
                                    pass
                        
                        results.append({
                            'text': text[:300],
                            'author': {'username': account},
                            'id': tweet_url.split('/')[-1] if tweet_url else '',
                            'posted': post_time,
                            'engagement': {'likes': likes, 'retweets': retweets}
                        })
                        
            except Exception as e:
                self.log(f"抓取 @{account} 出错: {e}", 'WARNING')
                continue
        
        # 方法2：搜索关键词
        for query in search_queries[:3]:
            try:
                url = f"{working_instance}/search?f=tweets&q={query}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tweets = soup.select('.timeline-item')
                    
                    for tweet in tweets[:5]:
                        content_elem = tweet.select_one('.tweet-content')
                        if not content_elem:
                            continue
                        
                        text = content_elem.get_text(strip=True)
                        if len(text) < 20:
                            continue
                        
                        # 提取用户名
                        username_elem = tweet.select_one('.username')
                        username = username_elem.get_text(strip=True).replace('@', '') if username_elem else 'unknown'
                        
                        # 提取链接
                        link_elem = tweet.select_one('.tweet-link')
                        tweet_url = ""
                        if link_elem:
                            href = link_elem.get('href', '')
                            if href:
                                tweet_url = f"https://twitter.com{href}" if href.startswith('/') else href
                        
                        results.append({
                            'text': text[:300],
                            'author': {'username': username},
                            'id': tweet_url.split('/')[-1] if tweet_url else '',
                            'posted': self.yesterday,
                            'engagement': {'likes': 0, 'retweets': 0}
                        })
                        
            except Exception as e:
                continue
        
        self.log(f"Nitter获取 {len(results)} 条推文")
        return results
    
    def _search_twitter_via_rss(self, keywords):
        """通过Twitter RSS备用方案（最后回退）"""
        results = []
        
        # 使用第三方Twitter RSS服务
        rss_services = [
            # Nitter RSS
            'https://nitter.poast.org/{account}/rss',
            # RSS Bridge
            'https://rss.app/feeds/twitter/{account}.xml',
        ]
        
        ai_accounts = ['OpenAI', 'AnthropicAI', 'GoogleAI', 'DeepMind']
        
        for account in ai_accounts[:4]:
            for rss_template in rss_services:
                try:
                    rss_url = rss_template.format(account=account)
                    response = self.session.get(rss_url, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        items = soup.find_all('item')
                        
                        for item in items[:3]:
                            title_elem = item.find('title')
                            link_elem = item.find('link')
                            desc_elem = item.find('description')
                            
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            if not title or len(title) < 10:
                                continue
                            
                            link = ""
                            if link_elem:
                                link = link_elem.get_text(strip=True) or link_elem.get('href', '')
                            
                            results.append({
                                'text': title[:300],
                                'author': {'username': account},
                                'id': link.split('/')[-1] if link else '',
                                'posted': self.yesterday,
                                'engagement': {'likes': 0, 'retweets': 0}
                            })
                        
                        break  # 成功获取，跳过其他RSS服务
                        
                except Exception:
                    continue
        
        self.log(f"RSS备用方案获取 {len(results)} 条推文")
        return results
    
    def search_from_reddit(self):
        """从Reddit获取AI相关新闻（增强版：添加备用方案）"""
        results = []
        
        # Reddit AI相关子版块
        subreddits = [
            'artificial',
            'MachineLearning',
            'ChatGPT',
            'OpenAI',
            'LocalLLaMA',
            'singularity'
        ]
        
        # 方案1：直接访问Reddit JSON API
        for subreddit in subreddits:
            try:
                # 使用Reddit的JSON API（无需认证）
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10"
                headers = {
                    'User-Agent': 'AI News Collector Bot 1.0'
                }
                
                response = self.session.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        post_data = post.get('data', {})
                        
                        # 过滤条件：评分>50，且是近期帖子
                        score = post_data.get('score', 0)
                        if score < 50:
                            continue
                        
                        title = post_data.get('title', '')
                        permalink = post_data.get('permalink', '')
                        selftext = post_data.get('selftext', '')[:300]
                        created_utc = post_data.get('created_utc', 0)
                        
                        # 检查是否是近期帖子（24小时内）
                        if created_utc:
                            post_time = datetime.fromtimestamp(created_utc)
                            if (datetime.now() - post_time).days > 2:
                                continue
                        
                        if title and permalink:
                            results.append({
                                'title': title,
                                'url': f"https://www.reddit.com{permalink}",
                                'content': selftext,
                                'publish_time': self.yesterday,
                                'source': f"Reddit r/{subreddit}",
                                'engagement': {'likes': score}
                            })
                            
            except Exception as e:
                self.log(f"Reddit r/{subreddit} 抓取出错: {e}", 'WARNING')
                continue
        
        # 方案2：如果直接访问失败，尝试使用Reddit RSS
        if len(results) == 0:
            self.log("Reddit API不可用，尝试RSS备用方案...", 'INFO')
            results = self._search_reddit_via_rss(subreddits)
        
        self.log(f"Reddit获取 {len(results)} 条帖子")
        return results
    
    def _search_reddit_via_rss(self, subreddits):
        """通过RSS获取Reddit内容（备用方案）"""
        results = []
        
        for subreddit in subreddits[:4]:
            try:
                # Reddit RSS
                rss_url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
                response = self.session.get(rss_url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    entries = soup.find_all('entry')
                    
                    for entry in entries[:5]:
                        title_elem = entry.find('title')
                        link_elem = entry.find('link')
                        content_elem = entry.find('content')
                        
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        if not title or len(title) < 10:
                            continue
                        
                        link = link_elem.get('href', '') if link_elem else ""
                        content = ""
                        if content_elem:
                            content = self.clean_content(content_elem.get_text(strip=True))
                        
                        results.append({
                            'title': title,
                            'url': link,
                            'content': content[:200],
                            'publish_time': self.yesterday,
                            'source': f"Reddit r/{subreddit}",
                            'engagement': {'likes': 0}
                        })
                        
            except Exception:
                continue
        
        return results
    
    def search_from_bing_rss(self, queries):
        """从Bing RSS获取新闻（优化版：获取真实URL）"""
        results = []
        
        for query in queries[:3]:
            search_url = "https://www.bing.com/news/search"
            params = {
                'q': f'{query} {self.yesterday}',
                'format': 'rss',
                'count': 10
            }
            
            try:
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    items = soup.find_all('item')
                    
                    for item in items[:5]:
                        title_elem = item.find('title')
                        link_elem = item.find('link')
                        
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        
                        if not title:
                            continue
                        
                        # 尝试多种方式获取真实URL
                        url = ""
                        
                        # 方式1：直接获取link标签
                        if link_elem:
                            url = link_elem.get_text(strip=True) or link_elem.get('href', '')
                        
                        # 方式2：从news:url或entity元素获取
                        if not url or len(url) < 20:
                            news_url = item.find('news:url')
                            if news_url:
                                url = news_url.get_text(strip=True)
                        
                        # 方式3：尝试从URL推断或构建搜索链接
                        if not url or 'bing.com' in url:
                            # 使用搜索链接但标记为搜索结果
                            encoded_query = query.replace(' ', '+')
                            url = f"https://www.bing.com/news/search?q={encoded_query}+{self.yesterday}"
                        
                        # 清理内容
                        desc_elem = item.find('description')
                        desc = desc_elem.get_text(strip=True) if desc_elem else ""
                        desc = self.clean_content(desc)
                        
                        # 获取来源
                        source_elem = item.find('source')
                        source = source_elem.get_text(strip=True) if source_elem else "AI News"
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'content': desc,
                            'publish_time': self.yesterday,
                            'source': source
                        })
                        
            except Exception as e:
                continue
        
        return results
    
    def search_from_hacker_news(self):
        """从Hacker News获取AI相关新闻（使用官方API，稳定无反爬）"""
        results = []
        
        self.log("正在从Hacker News获取AI相关新闻...")
        
        # AI相关搜索关键词
        ai_keywords = [
            'AI', 'artificial intelligence', 'ChatGPT', 'GPT', 'LLM',
            'OpenAI', 'Anthropic', 'Claude', 'Gemini', 'Llama',
            'machine learning', 'deep learning', 'neural network',
            'AGI', 'transformer', 'diffusion', 'RLHF'
        ]
        
        try:
            # 方案1：使用HN Algolia Search API（最稳定，支持搜索）
            # 获取最近24小时的AI相关帖子
            yesterday_ts = int((datetime.now() - timedelta(days=1)).timestamp())
            
            for keyword in ai_keywords[:5]:  # 限制搜索数量避免过多请求
                try:
                    search_url = "https://hn.algolia.com/api/v1/search"
                    params = {
                        'query': keyword,
                        'tags': 'story',  # 只搜索故事（非评论）
                        'numericFilters': f'created_at_i>{yesterday_ts}',
                        'hitsPerPage': 10
                    }
                    
                    response = self.session.get(search_url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        hits = data.get('hits', [])
                        
                        for hit in hits:
                            title = hit.get('title', '')
                            if not title or len(title) < 10:
                                continue
                            
                            # 获取URL（优先使用原始链接，否则使用HN讨论页）
                            url = hit.get('url', '')
                            story_id = hit.get('objectID', '')
                            if not url:
                                url = f"https://news.ycombinator.com/item?id={story_id}"
                            
                            # 获取互动数据
                            points = hit.get('points', 0)
                            num_comments = hit.get('num_comments', 0)
                            
                            results.append({
                                'title': title,
                                'url': url,
                                'content': '',
                                'publish_time': self.yesterday,
                                'source': 'Hacker News',
                                'engagement': {
                                    'likes': points,
                                    'comments': num_comments
                                },
                                'hn_discussion': f"https://news.ycombinator.com/item?id={story_id}"
                            })
                            
                    time.sleep(0.2)  # 避免请求过快
                    
                except Exception as e:
                    self.log(f"HN搜索关键词 '{keyword}' 出错: {e}", 'WARNING')
                    continue
            
            # 方案2：获取HN首页热门帖子，筛选AI相关
            try:
                # 获取Top Stories
                top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
                response = self.session.get(top_url, timeout=10)
                
                if response.status_code == 200:
                    story_ids = response.json()[:50]  # 取前50个热门帖子
                    
                    for story_id in story_ids[:30]:  # 限制请求数量
                        try:
                            item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                            item_response = self.session.get(item_url, timeout=5)
                            
                            if item_response.status_code == 200:
                                item = item_response.json()
                                if not item:
                                    continue
                                
                                title = item.get('title', '').lower()
                                
                                # 检查是否与AI相关
                                is_ai_related = any(kw.lower() in title for kw in ai_keywords)
                                if not is_ai_related:
                                    continue
                                
                                original_title = item.get('title', '')
                                url = item.get('url', '')
                                if not url:
                                    url = f"https://news.ycombinator.com/item?id={story_id}"
                                
                                points = item.get('score', 0)
                                num_comments = item.get('descendants', 0)
                                
                                # 避免重复
                                if any(r['url'] == url for r in results):
                                    continue
                                
                                results.append({
                                    'title': original_title,
                                    'url': url,
                                    'content': '',
                                    'publish_time': self.yesterday,
                                    'source': 'Hacker News',
                                    'engagement': {
                                        'likes': points,
                                        'comments': num_comments
                                    },
                                    'hn_discussion': f"https://news.ycombinator.com/item?id={story_id}"
                                })
                                
                        except Exception:
                            continue
                        
                        time.sleep(0.1)  # API限流
                        
            except Exception as e:
                self.log(f"HN Top Stories获取出错: {e}", 'WARNING')
        
        except Exception as e:
            self.log(f"Hacker News抓取出错: {e}", 'ERROR')
        
        # 按点赞数排序，取前20条
        results = sorted(results, key=lambda x: x.get('engagement', {}).get('likes', 0), reverse=True)[:20]
        
        self.log(f"Hacker News获取 {len(results)} 条AI相关新闻")
        return results
    
    def search_from_meta_ai_blog(self):
        """从Meta AI (FAIR) Blog获取新闻"""
        results = []
        
        self.log("正在从Meta AI Blog获取新闻...")
        
        try:
            url = "https://ai.meta.com/blog/"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                seen_urls = set()
                
                # 优化的选择器列表（根据页面结构）
                # Meta AI Blog使用article标签和h2/h3标题
                article_selectors = [
                    'article h2 a',
                    'article h3 a',
                    '.blog-post h2 a',
                    '.blog-post h3 a',
                    '.blog-item a',
                    'a[href*="/blog/"][href*="meta"]',
                ]
                
                for selector in article_selectors:
                    links = soup.select(selector)
                    
                    for link in links[:15]:
                        href = link.get('href', '').strip()
                        if not href:
                            continue
                        
                        # 排除主页链接
                        if href in ['/', '/blog/', '/blog', 'https://ai.meta.com/blog/']:
                            continue
                        
                        # 补全相对链接
                        if not href.startswith('http'):
                            from urllib.parse import urljoin
                            href = urljoin('https://ai.meta.com', href)
                        
                        # 确保是博客文章链接
                        if '/blog/' not in href:
                            continue
                        
                        # 去重
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)
                        
                        # 获取标题
                        title = link.get_text(strip=True)
                        if not title:
                            title = link.get('title', '')
                        
                        # 清理标题
                        title = ' '.join(title.split())
                        
                        if not title or len(title) < 10 or len(title) > 300:
                            continue
                        
                        results.append({
                            'title': title,
                            'url': href,
                            'content': '',
                            'publish_time': self.yesterday,
                            'source': 'Meta AI Blog'
                        })
                    
                    if results:
                        break  # 如果找到了结果，不再尝试其他选择器
                
                # 备用方案：遍历所有链接查找博客文章
                if not results:
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href', '')
                        
                        # 检查是否是博客文章链接
                        if '/blog/' not in href:
                            continue
                        if href in ['/', '/blog/', '/blog']:
                            continue
                        
                        # 补全链接
                        if not href.startswith('http'):
                            href = f"https://ai.meta.com{href}"
                        
                        # 确保是ai.meta.com域名
                        if 'ai.meta.com' not in href:
                            continue
                        
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)
                        
                        title = link.get_text(strip=True)
                        # 过滤太短或太长的标题
                        if title and 10 < len(title) < 200:
                            # 排除导航类文字
                            if title.lower() not in ['blog', 'learn more', 'read more', 'view all']:
                                results.append({
                                    'title': title,
                                    'url': href,
                                    'content': '',
                                    'publish_time': self.yesterday,
                                    'source': 'Meta AI Blog'
                                })
            
            # 备用方案2：通过Bing搜索获取Meta AI Blog最新文章
            # （Meta AI Blog使用JavaScript渲染，直接抓取可能获取不到内容）
            if len(results) < 3:
                try:
                    search_url = "https://www.bing.com/news/search"
                    params = {
                        'q': 'site:ai.meta.com/blog',
                        'format': 'rss',
                        'count': 10
                    }
                    search_response = self.session.get(search_url, params=params, timeout=10)
                    
                    if search_response.status_code == 200:
                        search_soup = BeautifulSoup(search_response.text, 'html.parser')
                        items = search_soup.find_all('item')
                        
                        for item in items[:5]:
                            title_elem = item.find('title')
                            link_elem = item.find('link')
                            
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            link_href = ""
                            if link_elem:
                                link_href = link_elem.get_text(strip=True)
                            
                            if not title or len(title) < 10:
                                continue
                            
                            # 确保链接指向ai.meta.com
                            if link_href and 'ai.meta.com' in link_href and link_href not in seen_urls:
                                seen_urls.add(link_href)
                                results.append({
                                    'title': title,
                                    'url': link_href,
                                    'content': '',
                                    'publish_time': self.yesterday,
                                    'source': 'Meta AI Blog'
                                })
                                
                except Exception:
                    pass
                
        except Exception as e:
            self.log(f"Meta AI Blog抓取出错: {e}", 'ERROR')
        
        self.log(f"Meta AI Blog获取 {len(results)} 条新闻")
        return results[:10]  # 限制数量
    
    def search_from_microsoft_research_blog(self):
        """从Microsoft Research Blog获取AI相关新闻"""
        results = []
        
        self.log("正在从Microsoft Research Blog获取新闻...")
        
        try:
            # Microsoft Research Blog主页
            url = "https://www.microsoft.com/en-us/research/blog/"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                seen_urls = set()
                
                # 优化选择器，排除人员页面，只获取博客文章
                # 博客文章URL通常包含日期或特定路径模式
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    href = link.get('href', '').strip()
                    if not href:
                        continue
                    
                    # 补全相对链接
                    if not href.startswith('http'):
                        from urllib.parse import urljoin
                        href = urljoin('https://www.microsoft.com', href)
                    
                    # 只接受博客文章链接（包含/blog/且不是人员页面）
                    # 排除条件：
                    # - 人员页面 (/people/)
                    # - 主页 (/blog/ 本身)
                    # - 项目页面 (/project/)
                    # - 团队页面 (/group/)
                    if '/research/blog/' not in href:
                        continue
                    if '/people/' in href or '/project/' in href or '/group/' in href:
                        continue
                    if href.endswith('/blog/') or href.endswith('/blog'):
                        continue
                    
                    # 确保是microsoft.com域名
                    if 'microsoft.com' not in href:
                        continue
                    
                    # 去重
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # 获取标题
                    title = ""
                    # 尝试从链接内的标题元素获取
                    title_elem = link.find(['h2', 'h3', 'h4', 'span'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    if not title:
                        title = link.get_text(strip=True)
                    if not title:
                        title = link.get('title', '')
                    
                    # 清理标题
                    title = ' '.join(title.split())
                    
                    # 过滤无效标题
                    if not title or len(title) < 10 or len(title) > 300:
                        continue
                    # 排除导航类文字
                    if title.lower() in ['blog', 'read more', 'learn more', 'view all', 'microsoft research blog']:
                        continue
                    
                    results.append({
                        'title': title,
                        'url': href,
                        'content': '',
                        'publish_time': self.yesterday,
                        'source': 'Microsoft Research Blog'
                    })
            
            # 尝试获取AI专题页面（RSS或API）
            if len(results) < 3:
                try:
                    # 尝试RSS Feed
                    rss_url = "https://www.microsoft.com/en-us/research/feed/"
                    rss_response = self.session.get(rss_url, timeout=10)
                    
                    if rss_response.status_code == 200:
                        rss_soup = BeautifulSoup(rss_response.text, 'html.parser')
                        items = rss_soup.find_all('item')
                        
                        for item in items[:10]:
                            title_elem = item.find('title')
                            link_elem = item.find('link')
                            
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            link_href = ""
                            if link_elem:
                                link_href = link_elem.get_text(strip=True) or link_elem.next_sibling
                                if link_href:
                                    link_href = str(link_href).strip()
                            
                            if not title or not link_href or len(title) < 10:
                                continue
                            
                            # 排除人员页面
                            if '/people/' in link_href:
                                continue
                            
                            if link_href in seen_urls:
                                continue
                            seen_urls.add(link_href)
                            
                            results.append({
                                'title': title,
                                'url': link_href,
                                'content': '',
                                'publish_time': self.yesterday,
                                'source': 'Microsoft Research'
                            })
                            
                except Exception:
                    pass
                
        except Exception as e:
            self.log(f"Microsoft Research Blog抓取出错: {e}", 'ERROR')
        
        self.log(f"Microsoft Research Blog获取 {len(results)} 条新闻")
        return results[:10]  # 限制数量
    
    def search_from_chinese_sources(self):
        """从中文AI新闻源获取内容（增强国内访问稳定性）"""
        results = []
        
        # 中文AI新闻源
        chinese_sources = [
            {
                'name': '机器之心',
                'url': 'https://www.jiqizhixin.com/',
                'link_selector': 'a[href*="/article/"]',
                'title_attr': 'title'
            },
            {
                'name': '量子位',
                'url': 'https://www.qbitai.com/',
                'link_selector': 'a.post-title',
                'title_attr': None
            },
            {
                'name': '新智元',
                'url': 'https://www.ailab.cn/',
                'link_selector': 'a[href*="/article-"]',
                'title_attr': None
            },
            {
                'name': '36氪AI',
                'url': 'https://36kr.com/information/AI/',
                'link_selector': 'a.article-item-title',
                'title_attr': None
            }
        ]
        
        for source in chinese_sources:
            try:
                response = self.session.get(source['url'], timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.select(source['link_selector'])
                    
                    seen_urls = set()
                    for link in links[:5]:
                        url = link.get('href', '').strip()
                        if not url:
                            continue
                        
                        # 补全相对链接
                        if not url.startswith('http'):
                            from urllib.parse import urljoin
                            url = urljoin(source['url'], url)
                        
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        
                        # 获取标题
                        if source.get('title_attr'):
                            title = link.get(source['title_attr'], '')
                        else:
                            title = link.get_text(strip=True)
                        
                        if not title or len(title) < 5:
                            continue
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'content': '',
                            'publish_time': self.yesterday,
                            'source': source['name']
                        })
                        
            except Exception as e:
                self.log(f"抓取 {source['name']} 出错: {e}", 'WARNING')
                continue
        
        self.log(f"中文新闻源获取 {len(results)} 条新闻")
        return results
    
    def extract_from_websites(self, urls):
        """从指定网站提取内容（优化版）"""
        results = []
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 提取标题
                    title_elem = soup.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    if not title:
                        # 尝试从title标签获取
                        title_tag = soup.find('title')
                        if title_tag:
                            title = title_tag.get_text(strip=True)
                    
                    if not title:
                        continue
                    
                    # 提取主要内容
                    content_parts = []
                    for p in soup.find_all('p')[:15]:
                        text = p.get_text(strip=True)
                        if len(text) > 30:  # 过滤短文本
                            content_parts.append(text)
                    
                    content = ' '.join(content_parts)
                    content = self.clean_content(content)
                    
                    # 确保有URL
                    if not self.is_valid_url(url):
                        continue
                    
                    # 提取来源
                    source = url.split('/')[2]
                    
                    results.append({
                        'title': title,
                        'source': source,
                        'content': content,
                        'url': url,
                        'publish_time': self.yesterday
                    })
                    
            except Exception as e:
                self.log(f"提取 {url} 出错: {e}", 'WARNING')
                continue
        
        self.log(f"网站提取获取 {len(results)} 条有效新闻")
        return results
    
    def calculate_score(self, news_item):
        """
        计算新闻综合评分（增强版：支持社交媒体来源）
        评分维度：
        - 重要性: 35% (重大突破、产品发布、政策变化等)
        - 权威性: 25% (来源可信度)
        - 传播度: 20% (社交指标)
        - 创新性: 10% (技术创新)
        - 时效性: 10% (发布时间)
        """
        importance = 3  # 基础分降低
        authority = 5
        spread = 5
        innovation = 3
        timeliness = 5
        
        title = news_item.get('title', '').lower()
        source = news_item.get('source', '').lower()
        
        # === 重要性评估 (35%权重) ===
        # 重大事件关键词
        major_keywords = [
            'breakthrough', 'major', 'significant', 'warning', 'alert',
            'critical', 'emergency', 'crisis', 'major update', 'major release'
        ]
        # 发布类关键词
        launch_keywords = [
            'launch', 'release', 'announce', 'unveil', 'debut', 'introduce',
            'launches', 'releases', 'announces', 'unveils', 'new model'
        ]
        # 商业类关键词
        business_keywords = [
            'acquire', 'acquisition', 'partnership', 'collaboration', 'invest',
            'funding', 'ipo', 'public', 'deal', 'merge'
        ]
        # 政策类关键词
        policy_keywords = [
            'regulation', 'policy', 'law', 'ban', 'restriction', 'government',
            'congress', 'parliament', 'EU', 'China', 'US'
        ]
        
        importance_score = 0
        for keyword in major_keywords:
            if keyword in title:
                importance_score += 2
                break
        
        for keyword in launch_keywords:
            if keyword in title:
                importance_score += 3
                break
        
        for keyword in business_keywords:
            if keyword in title:
                importance_score += 2
                break
        
        for keyword in policy_keywords:
            if keyword in title:
                importance_score += 3
                break
        
        # 限制重要性分数范围
        importance = min(10, max(3, 3 + importance_score))
        
        # === 权威性评估 (25%权重) ===
        # 一级权威来源（AI公司官方、顶级媒体）
        top_authoritative = [
            'openai.com', 'anthropic.com', 'deepmind.google', 'ai.googleblog.com',
            'blog.google', 'ai.google', 'ai.meta.com', 'microsoft.com/en-us/research',
            'reuters.com', 'bloomberg.com', 'wsj.com', 'nytimes.com'
        ]
        # 二级权威来源（科技媒体、技术社区）
        second_authoritative = [
            'techcrunch.com', 'wired.com', 'theverge.com', 'arstechnica.com',
            'mit.edu', 'stanford.edu', 'google.com', 'meta.com', 'microsoft.com',
            'amazon.com', 'apple.com', 'nvidia.com', 'venturebeat.com',
            'news.ycombinator.com', 'hn.algolia.com'  # Hacker News
        ]
        # 社交媒体来源（Twitter、Reddit）
        social_sources = ['twitter', 'reddit']
        
        authority = 5  # 基础分
        for src in top_authoritative:
            if src in source:
                authority = 9
                break
        if authority == 5:
            for src in second_authoritative:
                if src in source:
                    authority = 7
                    break
        if authority == 5:
            for src in social_sources:
                if src in source:
                    authority = 6  # 社交媒体基础分稍低
                    break
        
        # === 传播度评估 (20%权重) - 新增 ===
        spread = 5  # 基础分
        engagement = news_item.get('engagement', {})
        if isinstance(engagement, dict):
            likes = engagement.get('likes', 0)
            if likes > 1000:
                spread = 9
            elif likes > 500:
                spread = 8
            elif likes > 100:
                spread = 7
            elif likes > 50:
                spread = 6
        
        # === 创新性评估 (10%权重) ===
        innovation_keywords = [
            'new', 'first', 'innovative', 'revolutionary', 'novel',
            'open source', 'framework', 'architecture', 'prototype',
            'gpt-5', 'gpt-4.5', 'claude 4', 'llama 4', 'mistral large'
        ]
        
        innovation = 5
        for keyword in innovation_keywords:
            if keyword in title:
                innovation += 2
                break
        innovation = min(10, innovation)
        
        # === 时效性评估 (10%权重) ===
        # 已经是前一天的新闻
        timeliness = 6  # 基础分
        publish_time = news_item.get('publish_time', '')
        if self.yesterday in publish_time:
            timeliness = 8  # 精确匹配前一天
        
        # 计算综合评分（调整权重）
        total_score = (
            importance * 0.35 +  # 重要性35%
            authority * 0.25 +   # 权威性25%
            spread * 0.20 +      # 传播度20%
            innovation * 0.10 +  # 创新性10%
            timeliness * 0.10    # 时效性10%
        )
        
        return {
            'importance': importance,
            'authority': authority,
            'spread': spread,
            'innovation': innovation,
            'timeliness': timeliness,
            'total_score': round(total_score, 2)
        }
    
    def translate_news(self, news_item):
        """翻译新闻为中文（使用Google翻译API）"""
        # 翻译标题（使用Google翻译，确保标题为中文）
        title = news_item.get('title', '')
        translated_title = self.translate_title(title)
        
        # 翻译内容摘要（同样使用Google翻译API进行完整汉化）
        content = news_item.get('content', '')
        translated_content = self.translate_content(content) if content else ''
        
        # 来源保持原样
        source = news_item.get('source', '')
        
        return {
            **news_item,
            'title': translated_title,
            'content': translated_content,
            'source': source,
            'original_title': title,  # 保存原文标题
            'original_content': content  # 保存原文内容
        }
    
    def translate_content(self, content):
        """
        翻译内容摘要为中文（使用Google翻译API）
        对长文本进行分段翻译，避免超出API限制
        """
        if not content or not content.strip():
            return content
        
        # 如果文本已经主要是中文，直接返回
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(re.sub(r'\s', '', content))
        if total_chars > 0 and chinese_chars / total_chars > 0.6:
            return content
        
        # 对于较短的内容，直接翻译
        if len(content) <= 500:
            return self.google_translate(content)
        
        # 对于较长的内容，按句子分段翻译，避免超出API限制
        # 按句号、问号、感叹号分割
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        translated_parts = []
        current_batch = ""
        
        for sentence in sentences:
            # 如果当前批次加上新句子不超过500字符，则合并
            if len(current_batch) + len(sentence) <= 500:
                current_batch += (" " if current_batch else "") + sentence
            else:
                # 翻译当前批次
                if current_batch:
                    translated_batch = self.google_translate(current_batch)
                    translated_parts.append(translated_batch)
                current_batch = sentence
        
        # 翻译最后一个批次
        if current_batch:
            translated_batch = self.google_translate(current_batch)
            translated_parts.append(translated_batch)
        
        # 合并所有翻译结果
        return " ".join(translated_parts)
    
    def collect_all_news(self):
        """
        收集所有平台的AI新闻（增强版 - RSS优先策略）
        策略优先级：
        1. RSS Feeds（最稳定，反爬风险最低，特别适合GitHub Actions）
        2. 官方API（如Hacker News API）
        3. 网页抓取（作为补充）
        """
        self.log(f"开始收集 {self.yesterday} 的AI新闻...")
        
        # ============== 第一优先级：RSS Feeds ==============
        # RSS是最稳定的数据源，解析简单，反爬风险低
        rss_results = self.fetch_rss_feeds()
        
        # 处理RSS结果
        for item in rss_results:
            if isinstance(item, dict) and 'title' in item and 'url' in item:
                if self.is_valid_url(item['url']):
                    # RSS已有authority_score，直接使用
                    auth_score = item.pop('authority_score', 7)
                    score = self.calculate_score(item)
                    # 使用RSS提供的权威性分数
                    score['authority'] = auth_score
                    # 重新计算总分
                    score['total_score'] = round(
                        score['importance'] * 0.35 +
                        score['authority'] * 0.25 +
                        score['spread'] * 0.20 +
                        score['innovation'] * 0.10 +
                        score['timeliness'] * 0.10,
                        2
                    )
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat(),
                        'fetch_method': 'RSS'
                    })
        
        # ============== 第二优先级：官方API ==============
        # Hacker News等提供稳定API的源
        
        # 扩展的搜索关键词（参考项目1）
        web_queries = [
            'artificial intelligence',
            'AI machine learning',
            'ChatGPT OpenAI',
            'Claude Anthropic',
            'GPT-4 LLM',
            'AI regulation policy',
            'AI technology breakthrough',
            'Gemini Google AI',
            'Llama Meta AI',
            'AI startup funding'
        ]
        
        # Twitter搜索关键词（参考项目1）
        twitter_keywords = [
            'AI OR artificial intelligence OR ChatGPT OR Claude OR GPT OR LLM',
            'OpenAI OR Anthropic OR DeepMind',
            'AI breakthrough OR AI release OR AI launch'
        ]
        
        # 官方博客URL（扩展 - 增加三大AI巨头官方博客）
        websites = [
            # Anthropic官方
            'https://www.anthropic.com/news',
            'https://www.anthropic.com/research',
            # OpenAI官方
            'https://openai.com/blog',
            'https://openai.com/news',
            # Google AI官方
            'https://blog.google/technology/ai/',
            'https://ai.googleblog.com/',
            'https://deepmind.google/blog/',
            # 其他AI巨头
            'https://ai.meta.com/blog/',
            'https://blogs.nvidia.com/blog/category/deep-learning/',
            'https://www.microsoft.com/en-us/ai/blog/'
        ]
        
        # 多源并行收集（RSS已单独获取，这里获取其他源）
        with ThreadPoolExecutor(max_workers=8) as executor:
            web_future = executor.submit(self.search_news_from_web, web_queries)
            website_future = executor.submit(self.extract_from_websites, websites)
            twitter_future = executor.submit(self.search_from_twitter, twitter_keywords)
            reddit_future = executor.submit(self.search_from_reddit)
            chinese_future = executor.submit(self.search_from_chinese_sources)
            # Hacker News API（稳定可靠）
            hn_future = executor.submit(self.search_from_hacker_news)
            meta_ai_future = executor.submit(self.search_from_meta_ai_blog)
            ms_research_future = executor.submit(self.search_from_microsoft_research_blog)
            
            web_results = web_future.result()
            website_results = website_future.result()
            twitter_results = twitter_future.result()
            reddit_results = reddit_future.result()
            chinese_results = chinese_future.result()
            # 获取新数据源结果
            hn_results = hn_future.result()
            meta_ai_results = meta_ai_future.result()
            ms_research_results = ms_research_future.result()
        
        # 处理搜索结果（过滤无URL的新闻）
        for item in web_results:
            if isinstance(item, dict) and 'title' in item and 'url' in item:
                if self.is_valid_url(item['url']):
                    score = self.calculate_score(item)
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat()
                    })
        
        # 处理网站提取结果
        for result in website_results:
            if isinstance(result, dict) and 'title' in result:
                score = self.calculate_score(result)
                self.news_items.append({
                    **result,
                    'score': score,
                    'collection_time': datetime.now().isoformat()
                })
        
        # 处理Twitter结果（参考项目1）
        for tweet in twitter_results:
            if isinstance(tweet, dict):
                # 构建推文数据
                tweet_text = tweet.get('text', '')[:200]
                author = tweet.get('author', {})
                username = author.get('username', 'unknown') if isinstance(author, dict) else 'unknown'
                tweet_id = tweet.get('id', '')
                
                score = self.calculate_score({
                    'title': tweet_text[:100],
                    'source': f"Twitter @{username}"
                })
                
                # 添加社交指标到评分
                engagement = tweet.get('engagement', {})
                likes = engagement.get('likes', 0) if isinstance(engagement, dict) else 0
                if likes > 1000:
                    score['total_score'] = min(10, score['total_score'] + 1)
                
                self.news_items.append({
                    'title': tweet_text,
                    'source': f"Twitter @{username}",
                    'url': f"https://twitter.com/{username}/status/{tweet_id}",
                    'publish_time': tweet.get('posted', self.yesterday),
                    'engagement': engagement,
                    'score': score,
                    'collection_time': datetime.now().isoformat()
                })
        
        # 处理Reddit结果
        for post in reddit_results:
            if isinstance(post, dict) and 'title' in post:
                score = self.calculate_score(post)
                
                # Reddit帖子评分加成（基于点赞数）
                engagement = post.get('engagement', {})
                likes = engagement.get('likes', 0) if isinstance(engagement, dict) else 0
                if likes > 500:
                    score['total_score'] = min(10, score['total_score'] + 0.5)
                
                self.news_items.append({
                    **post,
                    'score': score,
                    'collection_time': datetime.now().isoformat()
                })
        
        # 处理中文新闻源结果
        for item in chinese_results:
            if isinstance(item, dict) and 'title' in item:
                if self.is_valid_url(item.get('url', '')):
                    score = self.calculate_score(item)
                    # 中文源权威性加成
                    if item.get('source') in ['机器之心', '量子位', '新智元']:
                        score['authority'] = min(10, score.get('authority', 5) + 1)
                        score['total_score'] = min(10, score['total_score'] + 0.2)
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat()
                    })
        
        # 处理Hacker News结果（新增）
        for item in hn_results:
            if isinstance(item, dict) and 'title' in item:
                if self.is_valid_url(item.get('url', '')):
                    score = self.calculate_score(item)
                    # HN高分帖子加成（Y Combinator投资动向的风向标）
                    engagement = item.get('engagement', {})
                    likes = engagement.get('likes', 0) if isinstance(engagement, dict) else 0
                    if likes > 500:
                        score['spread'] = min(10, score.get('spread', 5) + 2)
                        score['total_score'] = min(10, score['total_score'] + 0.5)
                    elif likes > 200:
                        score['spread'] = min(10, score.get('spread', 5) + 1)
                        score['total_score'] = min(10, score['total_score'] + 0.3)
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat()
                    })
        
        # 处理Meta AI Blog结果（新增）
        for item in meta_ai_results:
            if isinstance(item, dict) and 'title' in item:
                if self.is_valid_url(item.get('url', '')):
                    score = self.calculate_score(item)
                    # Meta AI官方博客权威性加成（Llama系列模型发源地）
                    score['authority'] = min(10, score.get('authority', 5) + 2)
                    score['total_score'] = min(10, score['total_score'] + 0.3)
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat()
                    })
        
        # 处理Microsoft Research Blog结果（新增）
        for item in ms_research_results:
            if isinstance(item, dict) and 'title' in item:
                if self.is_valid_url(item.get('url', '')):
                    score = self.calculate_score(item)
                    # Microsoft Research权威性加成（Phi系列、AutoGen等重要成果）
                    score['authority'] = min(10, score.get('authority', 5) + 2)
                    score['total_score'] = min(10, score['total_score'] + 0.3)
                    self.news_items.append({
                        **item,
                        'score': score,
                        'collection_time': datetime.now().isoformat()
                    })
        
        self.log(f"收集完成，共获取 {len(self.news_items)} 条有效新闻")
        self.log(f"  📡 RSS Feeds: {len(rss_results)} 条 (优先级最高)")
        self.log(f"  - 网络搜索: {len(web_results)} 条")
        self.log(f"  - 官方博客: {len(website_results)} 条")
        self.log(f"  - Twitter: {len(twitter_results)} 条")
        self.log(f"  - Reddit: {len(reddit_results)} 条")
        self.log(f"  - 中文新闻源: {len(chinese_results)} 条")
        self.log(f"  - Hacker News API: {len(hn_results)} 条")
        self.log(f"  - Meta AI Blog: {len(meta_ai_results)} 条")
        self.log(f"  - Microsoft Research: {len(ms_research_results)} 条")
        
        return self.news_items
    
    def sort_and_filter(self, top_n=50):
        """排序并筛选新闻（优化版：更智能的去重）"""
        if not self.news_items:
            return []
        
        # 按综合评分排序
        sorted_news = sorted(
            self.news_items, 
            key=lambda x: x.get('score', {}).get('total_score', 0), 
            reverse=True
        )
        
        # 智能去重
        unique_news = []
        seen_hashes = set()
        
        for news in sorted_news:
            # 计算内容哈希（基于标题和URL）
            content = f"{news.get('title', '')}{news.get('url', '')}"
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            # 如果哈希重复，跳过
            if content_hash in seen_hashes:
                continue
            
            seen_hashes.add(content_hash)
            
            # 应用翻译
            translated_news = self.translate_news(news)
            unique_news.append(translated_news)
        
        return unique_news[:top_n]
    
    def save_reports(self):
        """保存报告（增强版）"""
        sorted_news = self.sort_and_filter(50)
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Markdown报告
        md_filename = f"ai_news_daily_{date_str}.md"
        md_filepath = os.path.join(self.output_dir, md_filename)
        
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(f"# AI新闻日报 - {self.yesterday}\n\n")
            f.write(f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("**数据来源**: 【RSS优先】TechCrunch、Wired、MIT Technology Review、Ars Technica、Hacker News、arXiv、Hugging Face、The Gradient | Twitter/X、Reddit、OpenAI官方博客、Anthropic官方博客、Google AI官方博客、Meta AI (FAIR) Blog、Microsoft Research Blog、DeepMind、NVIDIA、机器之心、量子位、36氪\n\n")
            f.write("---\n\n")
            
            for i, news in enumerate(sorted_news, 1):
                score = news.get('score', {})
                # 显示中文标题，但保留原文标题
                display_title = news.get('title', '无标题')
                original_title = news.get('original_title', '')
                if original_title and original_title != display_title:
                    display_title = f"{display_title}\n原文: {original_title}"
                
                f.write(f"### {i}. {display_title}\n\n")
                f.write(f"- **来源**: {news.get('source', '未知')}\n")
                f.write(f"- **发布时间**: {news.get('publish_time', self.yesterday)}\n")
                f.write(f"- **综合评分**: {score.get('total_score', 0)}/10\n")
                f.write(f"- **评分明细**: 重要性{score.get('importance', 0)} | 权威性{score.get('authority', 0)} | 传播度{score.get('spread', 0)} | 创新性{score.get('innovation', 0)} | 时效性{score.get('timeliness', 0)}\n")
                
                # 确保有原文链接
                url = news.get('url', '')
                if self.is_valid_url(url):
                    f.write(f"- **原文链接**: {url}\n")
                else:
                    f.write(f"- **原文链接**: 无\n")
                
                content = news.get('content', '')
                if content:
                    f.write(f"- **内容摘要**: {content}...\n\n")
                else:
                    f.write("\n")
                
                f.write("---\n\n")
        
        self.log(f"Markdown报告已保存: {md_filepath}")
        
        # Top 10 JSON文件（供推送脚本使用）
        top10 = sorted_news[:10]
        json_filename = f"ai_news_daily_{date_str}_top10.json"
        json_filepath = os.path.join(self.output_dir, json_filename)
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(top10, f, ensure_ascii=False, indent=2)
        
        self.log(f"Top 10 JSON已保存: {json_filepath}")
        
        return md_filepath, json_filepath, len(sorted_news)


def main():
    """主函数"""
    collector = AINewsCollector()
    
    try:
        # 采集新闻
        collector.collect_all_news()
        
        # 保存报告
        md_path, json_path, total_count = collector.save_reports()
        
        collector.log(f"✅ 任务完成！共处理 {total_count} 条新闻")
        collector.log(f"📄 报告路径: {md_path}")
        collector.log(f"📊 JSON路径: {json_path}")
        
        sys.exit(0)
        
    except Exception as e:
        collector.log(f"❌ 任务失败: {e}", 'ERROR')
        import traceback
        collector.log(traceback.format_exc(), 'ERROR')
        sys.exit(1)


if __name__ == '__main__':
    main()
