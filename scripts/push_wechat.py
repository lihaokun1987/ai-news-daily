#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻聚合助手 - 企业微信推送脚本
读取JSON格式的Top 10新闻，推送到企业微信
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path


class WeChatPusher:
    """企业微信机器人推送器"""
    
    def __init__(self, webhook_url=None):
        """初始化
        
        Args:
            webhook_url: 企业微信机器人Webhooks URL
        """
        self.webhook_url = webhook_url or os.environ.get('WECOM_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("未设置企业微信Webhooks URL")
    
    def format_markdown_content(self, news_list, date=None):
        """格式化新闻为Markdown内容
        
        Args:
            news_list: 新闻列表
            date: 新闻日期
            
        Returns:
            Markdown格式的内容
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        
        content = f"""## 🤖 AI新闻日报 Top10
**{date} | 自动聚合报告**
---
"""
        
        for i, news in enumerate(news_list, 1):
            score = news.get('score', {})
            title = news.get('title', '无标题')
            source = news.get('source', '未知来源')
            url = news.get('url', '')
            content_text = news.get('content', '')[:100]  # 缩短到100字符
            if len(news.get('content', '')) > 100:
                content_text += '...'
            
            # 清理标题中的特殊字符
            title = title.replace('**', '').replace('#', '').replace('\n', ' ')
            
            content += f"""**{i}. {title}**
> 📰 {source} | ⭐ {score.get('total_score', 0)}/10
> {content_text}
"""
            if url:
                content += f"> [查看原文]({url})\n"
            
            content += "\n---\n\n"
        
        content += f"""*📊 数据来源：Twitter/X、Anthropic、OpenAI、主流科技媒体等 | 自动聚合*
*🕐 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def push_to_wechat(self, news_list, date=None):
        """推送到企业微信
        
        Args:
            news_list: 新闻列表
            date: 新闻日期
            
        Returns:
            推送结果
        """
        markdown_content = self.format_markdown_content(news_list, date)
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            result = response.json()
            
            if result.get('errcode') == 0:
                print("✅ 推送成功!")
                return True, result
            else:
                print(f"❌ 推送失败: {result.get('errmsg')}")
                return False, result
                
        except Exception as e:
            print(f"❌ 推送出错: {e}")
            return False, str(e)
    
    def push_from_json(self, json_path, date=None):
        """从JSON文件读取新闻并推送
        
        Args:
            json_path: JSON文件路径
            date: 新闻日期
            
        Returns:
            推送结果
        """
        if not os.path.exists(json_path):
            print(f"❌ 文件不存在: {json_path}")
            return False, "File not found"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            news_list = json.load(f)
        
        print(f"📄 从 {json_path} 读取到 {len(news_list)} 条新闻")
        return self.push_to_wechat(news_list, date)


def find_latest_json(output_dir=None):
    """查找最新的新闻JSON文件
    
    Args:
        output_dir: 输出目录，默认为脚本所在目录的上级output目录
        
    Returns:
        最新JSON文件路径
    """
    if output_dir is None:
        # 获取脚本所在目录的上级目录下的output目录
        script_dir = Path(__file__).parent.parent
        output_dir = script_dir / 'output'
    
    if not os.path.exists(output_dir):
        return None
    
    json_files = []
    for filename in os.listdir(output_dir):
        if filename.endswith('_top10.json'):
            json_files.append(os.path.join(output_dir, filename))
    
    if not json_files:
        return None
    
    # 按修改时间排序，返回最新的
    json_files.sort(key=os.path.getmtime, reverse=True)
    return json_files[0]


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI新闻企业微信推送脚本')
    parser.add_argument('--json', '-j', type=str,
                       help='JSON文件路径，默认为output目录下的最新文件')
    parser.add_argument('--webhook', '-w', type=str,
                       help='企业微信Webhooks URL')
    parser.add_argument('--date', '-d', type=str,
                       help='新闻日期，格式为YYYY-MM-DD')
    parser.add_argument('--list', '-l', action='store_true',
                       help='列出可用的JSON文件')
    
    args = parser.parse_args()
    
    # 获取脚本所在目录的上级目录下的output目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / 'output'
    
    # 列出可用的JSON文件
    if args.list:
        print("可用的新闻JSON文件:")
        json_file = find_latest_json(output_dir)
        if json_file:
            print(f"  最新文件: {json_file}")
        else:
            print("  未找到JSON文件")
        return
    
    # 初始化推送器
    pusher = WeChatPusher(webhook_url=args.webhook)
    
    # 确定JSON文件路径
    json_path = args.json
    if not json_path:
        json_path = find_latest_json(output_dir)
        if not json_path:
            print("❌ 未找到新闻JSON文件，请先运行 collect_news.py")
            sys.exit(1)
    
    print(f"📰 使用新闻文件: {json_path}")
    
    # 推送新闻
    success, result = pusher.push_from_json(json_path, args.date)
    
    if success:
        print("✅ 推送完成!")
        sys.exit(0)
    else:
        print("❌ 推送失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
