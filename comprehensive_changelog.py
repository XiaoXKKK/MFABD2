#!/usr/bin/env python3
"""
综合变更日志生成脚本
自动合并同一次版本的所有正式版更新内容
"""

import os
import re
import requests
import json
from typing import List, Dict, Optional

def get_github_api_headers(token: str) -> Dict[str, str]:
    """获取 GitHub API 请求头"""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MFABD2-Changelog-Generator"
    }

def extract_minor_version(tag: str) -> Optional[str]:
    """从标签中提取次版本号"""
    match = re.match(r'^v(\d+\.\d+)\.\d+$', tag)
    return match.group(1) if match else None

def is_formal_release(tag: str) -> bool:
    """判断是否为正式版标签"""
    return bool(re.match(r'^v\d+\.\d+\.\d+$', tag))

def get_all_releases(owner: str, repo: str, token: str) -> List[Dict]:
    """获取仓库的所有 Release"""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = get_github_api_headers(token)
    
    releases = []
    page = 1
    while True:
        response = requests.get(f"{url}?page={page}&per_page=100", headers=headers)
        if response.status_code != 200:
            print(f"❌ 获取 Release 失败: {response.status_code}")
            break
            
        page_releases = response.json()
        if not page_releases:
            break
            
        releases.extend(page_releases)
        page += 1
        
        # 安全限制，最多获取 10 页
        if page > 10:
            break
    
    return releases

def extract_main_content(body: str) -> str:
    """提取主要内容（去除固定首尾）"""
    if not body:
        return ""
    
    # 移除固定结尾（如果有）
    pattern = r'^(.*?)(?=\n\[已有 Mirror酱 CDK|\n*$)'
    match = re.search(pattern, body, re.DOTALL)
    content = match.group(1).strip() if match else body
    
    return content

def build_comprehensive_changelog(current_tag: str, owner: str, repo: str, token: str) -> str:
    """构建完整的次版本变更历史"""
    
    # 只处理正式版
    if not is_formal_release(current_tag):
        print(f"⚠️  {current_tag} 不是正式版，跳过历史合并")
        return ""
    
    minor_version = extract_minor_version(current_tag)
    if not minor_version:
        print(f"❌ 无法从 {current_tag} 提取次版本号")
        return ""
    
    print(f"🔍 查找次版本 {minor_version} 的所有正式版 Release...")
    
    # 获取所有 Release
    all_releases = get_all_releases(owner, repo, token)
    
    # 过滤出同一次版本的正式版 Release
    minor_releases = []
    for release in all_releases:
        tag = release['tag_name']
        if (is_formal_release(tag) and 
            extract_minor_version(tag) == minor_version and
            not release['prerelease']):
            minor_releases.append(release)
    
    # 按版本号排序（新版在上）
    minor_releases.sort(key=lambda x: [int(n) for n in x['tag_name'][1:].split('.')], reverse=True)
    
    if len(minor_releases) <= 1:
        print(f"ℹ️  次版本 {minor_version} 只有一个正式版，无需合并历史")
        return ""
    
    print(f"📋 找到 {len(minor_releases)} 个正式版: {[r['tag_name'] for r in minor_releases]}")
    
    # 构建历史内容
    historical_content = ""
    for release in minor_releases[1:]:  # 跳过当前版本
        tag = release['tag_name']
        body = release['body'] or ""
        published_at = release['published_at'][:10] if release['published_at'] else "未知日期"
        
        main_content = extract_main_content(body)
        if not main_content.strip():
            continue
            
        historical_content += f"""
<details>
<summary>{tag} ({published_at}) 更新内容</summary>

{main_content}

</details>

"""
    
    if historical_content:
        final_content = f"""
## 📋 历史版本更新内容

{historical_content}
"""
        return final_content
    else:
        return ""

def main():
    """主函数"""
    current_tag = os.getenv('CURRENT_TAG')
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'sunyink')
    repo_name = os.getenv('GITHUB_REPOSITORY', 'MFABD2').split('/')[-1]
    
    if not current_tag:
        print("❌ 缺少 CURRENT_TAG 环境变量")
        return 1
        
    if not github_token:
        print("❌ 缺少 GITHUB_TOKEN 环境变量")
        return 1
    
    print(f"🚀 开始生成综合变更日志，当前版本: {current_tag}")
    print(f"📁 仓库: {repo_owner}/{repo_name}")
    
    # 生成历史内容
    historical_content = build_comprehensive_changelog(current_tag, repo_owner, repo_name, github_token)
    
    # 读取当前版本的 changelog
    current_changelog_path = 'current_changelog.md'
    if os.path.exists(current_changelog_path):
        with open(current_changelog_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        print(f"❌ 找不到当前版本 changelog 文件: {current_changelog_path}")
        return 1
    
    # 合并内容
    if historical_content:
        final_content = current_content + historical_content
        print("✅ 已合并历史版本内容")
    else:
        final_content = current_content
        print("ℹ️  未合并历史版本内容")
    
    # 写入最终文件
    with open('CHANGES.md', 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("✅ 综合变更日志生成完成: CHANGES.md")
    return 0

if __name__ == '__main__':
    exit(main())