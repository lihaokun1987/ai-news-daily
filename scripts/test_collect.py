#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线测试脚本 - 测试新闻抓取功能（V2）
"""

import sys
import os

# 确保可以导入主脚本
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collect_news import AINewsCollector
from datetime import datetime

def test_collect():
    """测试新闻抓取功能"""
    print("=" * 60)
    print("🧪 AI新闻抓取功能离线测试 V2")
    print("=" * 60)
    print()
    
    collector = AINewsCollector()
    
    print(f"📅 目标日期: {collector.yesterday}")
    print(f"📁 输出目录: {collector.output_dir}")
    print()
    
    # 分别测试各个数据源
    print("-" * 60)
    print("1️⃣ 测试网络搜索（Bing RSS）...")
    print("-" * 60)
    web_queries = ['AI breakthrough', 'ChatGPT OpenAI', 'Claude Anthropic']
    web_results = collector.search_news_from_web(web_queries)
    print(f"   ✅ 获取 {len(web_results)} 条新闻")
    if web_results:
        print(f"   📰 示例: {web_results[0].get('title', '')[:60]}...")
    print()
    
    print("-" * 60)
    print("2️⃣ 测试Twitter/X抓取...")
    print("-" * 60)
    twitter_keywords = ['AI', 'ChatGPT', 'LLM']
    twitter_results = collector.search_from_twitter(twitter_keywords)
    print(f"   ✅ 获取 {len(twitter_results)} 条推文")
    if twitter_results:
        sample = twitter_results[0]
        author = sample.get('author', {})
        username = author.get('username', 'unknown') if isinstance(author, dict) else 'unknown'
        print(f"   🐦 示例: @{username}: {sample.get('text', '')[:50]}...")
    print()
    
    print("-" * 60)
    print("3️⃣ 测试Reddit抓取...")
    print("-" * 60)
    reddit_results = collector.search_from_reddit()
    print(f"   ✅ 获取 {len(reddit_results)} 条帖子")
    if reddit_results:
        print(f"   📱 示例: [{reddit_results[0].get('source', '')}] {reddit_results[0].get('title', '')[:50]}...")
    print()
    
    print("-" * 60)
    print("4️⃣ 测试中文新闻源抓取...")
    print("-" * 60)
    chinese_results = collector.search_from_chinese_sources()
    print(f"   ✅ 获取 {len(chinese_results)} 条新闻")
    if chinese_results:
        print(f"   📝 示例: [{chinese_results[0].get('source', '')}] {chinese_results[0].get('title', '')[:40]}...")
    print()
    
    print("-" * 60)
    print("5️⃣ 测试官方博客抓取...")
    print("-" * 60)
    websites = [
        'https://www.anthropic.com/news',
        'https://openai.com/blog',
    ]
    blog_results = collector.extract_from_websites(websites)
    print(f"   ✅ 获取 {len(blog_results)} 条内容")
    if blog_results:
        print(f"   📝 示例: {blog_results[0].get('title', '')[:60]}...")
    print()
    
    # 汇总并生成报告
    print("=" * 60)
    print("📊 汇总测试结果并生成报告...")
    print("=" * 60)
    
    # 手动添加结果到collector
    for item in web_results:
        if isinstance(item, dict) and 'title' in item:
            if collector.is_valid_url(item.get('url', '')):
                score = collector.calculate_score(item)
                collector.news_items.append({
                    **item,
                    'score': score,
                    'collection_time': datetime.now().isoformat()
                })
    
    for tweet in twitter_results:
        if isinstance(tweet, dict):
            tweet_text = tweet.get('text', '')[:200]
            author = tweet.get('author', {})
            username = author.get('username', 'unknown') if isinstance(author, dict) else 'unknown'
            tweet_id = tweet.get('id', '')
            
            score = collector.calculate_score({
                'title': tweet_text[:100],
                'source': f"Twitter @{username}"
            })
            
            collector.news_items.append({
                'title': tweet_text,
                'source': f"Twitter @{username}",
                'url': f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else f"https://twitter.com/{username}",
                'publish_time': tweet.get('posted', collector.yesterday),
                'engagement': tweet.get('engagement', {}),
                'score': score,
                'collection_time': datetime.now().isoformat()
            })
    
    for post in reddit_results:
        if isinstance(post, dict) and 'title' in post:
            score = collector.calculate_score(post)
            collector.news_items.append({
                **post,
                'score': score,
                'collection_time': datetime.now().isoformat()
            })
    
    for item in chinese_results:
        if isinstance(item, dict) and 'title' in item:
            if collector.is_valid_url(item.get('url', '')):
                score = collector.calculate_score(item)
                collector.news_items.append({
                    **item,
                    'score': score,
                    'collection_time': datetime.now().isoformat()
                })
    
    for result in blog_results:
        if isinstance(result, dict) and 'title' in result:
            score = collector.calculate_score(result)
            collector.news_items.append({
                **result,
                'score': score,
                'collection_time': datetime.now().isoformat()
            })
    
    print(f"\n📈 总计收集: {len(collector.news_items)} 条新闻")
    print(f"   - 网络搜索: {len(web_results)} 条")
    print(f"   - Twitter: {len(twitter_results)} 条")
    print(f"   - Reddit: {len(reddit_results)} 条")
    print(f"   - 中文新闻源: {len(chinese_results)} 条")
    print(f"   - 官方博客: {len(blog_results)} 条")
    
    # 保存报告
    if collector.news_items:
        md_path, json_path, total_count = collector.save_reports()
        
        print()
        print("=" * 60)
        print("✅ 测试完成！")
        print("=" * 60)
        print(f"📄 Markdown报告: {md_path}")
        print(f"📊 JSON文件: {json_path}")
        print(f"📰 有效新闻数: {total_count}")
        
        # 显示Top 5新闻
        print()
        print("-" * 60)
        print("🏆 Top 5 新闻预览:")
        print("-" * 60)
        sorted_news = collector.sort_and_filter(5)
        for i, news in enumerate(sorted_news, 1):
            score = news.get('score', {}).get('total_score', 0)
            source = news.get('source', '未知')
            title = news.get('title', '无标题')[:50]
            print(f"  {i}. [{score}/10] [{source}] {title}...")
    else:
        print()
        print("⚠️ 未能收集到任何新闻，请检查网络连接")


if __name__ == '__main__':
    test_collect()
