#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻聚合助手 - 企业微信推送脚本
读取JSON格式的Top 10新闻，推送到企业微信
"""
import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path


# 企业微信 Markdown 消息内容长度限制
WECOM_MAX_LENGTH = 4096
# 安全边界，预留一些空间
WECOM_SAFE_LENGTH = 3800


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
    
    def format_single_news(self, news, index):
        """格式化单条新闻为Markdown内容
        
        Args:
            news: 新闻数据
            index: 新闻序号（从1开始）
            
        Returns:
            Markdown格式的单条新闻内容
        """
        score = news.get('score', {})
        title = news.get('title', '无标题')
        source = news.get('source', '未知来源')
        url = news.get('url', '')
        content_text = news.get('content', '')[:100]  # 缩短到100字符
        if len(news.get('content', '')) > 100:
            content_text += '...'
        
        # 清理标题中的特殊字符
        title = title.replace('**', '').replace('#', '').replace('\n', ' ')
        
        news_content = f"""**{index}. {title}**
> 📰 {source} | ⭐ {score.get('total_score', 0)}/10
> {content_text}
"""
        if url:
            news_content += f"> [查看原文]({url})\n"
        
        news_content += "\n---\n\n"
        return news_content
    
    def format_header(self, date, part=None, total_parts=None):
        """格式化消息头部
        
        Args:
            date: 日期
            part: 当前部分序号（如果分多次发送）
            total_parts: 总部分数（如果分多次发送）
            
        Returns:
            Markdown格式的头部内容
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        
        if part and total_parts and total_parts > 1:
            header = f"""## 🤖 AI新闻日报 Top10 ({part}/{total_parts})
**{date} | 自动聚合报告**
---
"""
        else:
            header = f"""## 🤖 AI新闻日报 Top10
**{date} | 自动聚合报告**
---
"""
        return header
    
    def format_footer(self):
        """格式化消息尾部
        
        Returns:
            Markdown格式的尾部内容
        """
        return f"""*📊 数据来源：Twitter/X、Anthropic、OpenAI、主流科技媒体等 | 自动聚合*
*🕐 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    def format_markdown_content(self, news_list, date=None):
        """格式化新闻为Markdown内容
        
        Args:
            news_list: 新闻列表
            date: 新闻日期
            
        Returns:
            Markdown格式的内容
        """
        content = self.format_header(date)
        
        for i, news in enumerate(news_list, 1):
            content += self.format_single_news(news, i)
        
        content += self.format_footer()
        
        return content
    
    def split_news_into_batches(self, news_list, date=None):
        """将新闻列表分批，确保每批内容不超过长度限制
        
        Args:
            news_list: 新闻列表
            date: 新闻日期
            
        Returns:
            分批后的Markdown内容列表
        """
        # 首先尝试完整内容
        full_content = self.format_markdown_content(news_list, date)
        
        if len(full_content) <= WECOM_SAFE_LENGTH:
            return [full_content]
        
        print(f"⚠️ 内容长度 {len(full_content)} 超过限制 {WECOM_SAFE_LENGTH}，将分批推送")
        
        # 计算需要分成多少批
        batches = []
        current_news = []
        header_len = len(self.format_header(date, 1, 2))  # 预估头部长度
        footer_len = len(self.format_footer())
        
        current_length = header_len + footer_len
        
        for i, news in enumerate(news_list):
            news_content = self.format_single_news(news, i + 1)
            news_len = len(news_content)
            
            # 如果加上这条新闻会超限，就开始新的批次
            if current_length + news_len > WECOM_SAFE_LENGTH and current_news:
                batches.append(current_news)
                current_news = []
                current_length = header_len + footer_len
            
            current_news.append((i + 1, news))  # 保存原始序号
            current_length += news_len
        
        # 添加最后一批
        if current_news:
            batches.append(current_news)
        
        # 格式化每批内容
        total_parts = len(batches)
        result = []
        
        for part_num, batch in enumerate(batches, 1):
            content = self.format_header(date, part_num, total_parts)
            for original_index, news in batch:
                content += self.format_single_news(news, original_index)
            
            # 只在最后一批加上脚注
            if part_num == total_parts:
                content += self.format_footer()
            
            result.append(content)
        
        print(f"📦 已分成 {len(result)} 批推送")
        return result
    
    def _send_single_message(self, markdown_content):
        """发送单条Markdown消息
        
        Args:
            markdown_content: Markdown内容
            
        Returns:
            (success, result) 元组
        """
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
                return True, result
            else:
                print(f"❌ 推送失败: {result.get('errmsg')}")
                return False, result
                
        except Exception as e:
            print(f"❌ 推送出错: {e}")
            return False, str(e)
    
    def push_to_wechat(self, news_list, date=None):
        """推送到企业微信（支持分批推送）
        
        Args:
            news_list: 新闻列表
            date: 新闻日期
            
        Returns:
            推送结果
        """
        # 分批处理内容
        batches = self.split_news_into_batches(news_list, date)
        
        all_success = True
        results = []
        
        for i, batch_content in enumerate(batches, 1):
            print(f"📤 推送第 {i}/{len(batches)} 批 (内容长度: {len(batch_content)} 字符)")
            
            success, result = self._send_single_message(batch_content)
            results.append(result)
            
            if not success:
                all_success = False
                print(f"❌ 第 {i} 批推送失败")
                break
            else:
                print(f"✅ 第 {i} 批推送成功")
            
            # 如果不是最后一批，稍微等待一下，避免被限流
            if i < len(batches):
                time.sleep(1)
        
        if all_success:
            print("✅ 全部推送成功!")
        
        return all_success, results
    
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
