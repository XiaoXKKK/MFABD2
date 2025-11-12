#!/usr/bin/env python3
"""
历史版本管理模块
"""

import os
import re
import sys
import requests
from typing import List, Dict, Optional
from version_rules import filter_valid_versions, sort_versions, is_valid_formal_version

class HistoryManager:
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MFABD2-History-Manager"
        }
    
    def fetch_all_releases(self) -> List[Dict]:
        """获取所有releases，失败则终止作业"""
        print("获取GitHub Releases...")
        url = f"{self.base_url}/releases"
        releases = []
        page = 1
        
        try:
            while True:
                response = requests.get(f"{url}?page={page}&per_page=100", headers=self.headers, timeout=30)
                if response.status_code != 200:
                    raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
                page_releases = response.json()
                if not page_releases:
                    break
                    
                releases.extend(page_releases)
                page += 1
                
                if page > 10:  # 安全限制
                    print("警告: 达到页面限制，停止获取更多releases")
                    break
            
            print(f"成功获取 {len(releases)} 个releases")
            return releases
            
        except Exception as e:
            print(f"❌ 获取Releases失败: {e}")
            sys.exit(1)
    
        """解析版本号，带错误处理（支持内测版/开发版）"""
        try:
            # 提取基础版本号部分
            # v2.3.7-beta.251112.b91bb42 → v2.3.7 → (2, 3, 7)
            base_tag = re.sub(r'(-beta\.\d+\.[a-f0-9]+|-ci\.\d+\.[a-f0-9]+)$', '', tag)
            clean_tag = base_tag.lstrip('v')
            parts = clean_tag.split('.')
            if len(parts) != 3:
                raise ValueError(f"版本格式异常: {tag}")
            return tuple(int(part) for part in parts)
        except Exception as e:
            print(f"❌ 版本解析失败: {tag} - {e}")
            sys.exit(1)
    
    def get_minor_version_series(self, current_tag: str) -> List[Dict]:
        """获取同次版本的所有正式版Release"""
        try:
            current_major, current_minor, _ = self.parse_version(current_tag)
        except SystemExit:
            # 如果版本解析失败（比如当前是内测版），使用最新正式版作为基准
            print(f"当前标签 {current_tag} 不是正式版，使用最新正式版作为历史基准")
            all_releases = self.fetch_all_releases()
            formal_releases = [r for r in all_releases if is_valid_formal_version(r['tag_name'])]
            if formal_releases:
                latest_formal = max(formal_releases, key=lambda r: self.parse_version(r['tag_name']))
                current_major, current_minor, _ = self.parse_version(latest_formal['tag_name'])
            else:
                print("没有找到任何正式版，跳过历史版本")
                return []
        
        all_releases = self.fetch_all_releases()
        
        relevant_releases = []
        for release in all_releases:
            tag = release['tag_name']
            if not is_valid_formal_version(tag):
                continue
                
            try:
                major, minor, _ = self.parse_version(tag)
                if major == current_major and minor <= current_minor:
                    # 排除当前版本自身（如果是正式版）
                    if tag != current_tag:
                        relevant_releases.append(release)
            except SystemExit:
                # 跳过解析失败的版本
                continue
        
        # 按版本号排序（从新到旧）
        relevant_releases.sort(key=lambda r: self.parse_version(r['tag_name']), reverse=True)
        
        print(f"找到 {len(relevant_releases)} 个相关历史版本")
        return relevant_releases
        
        # 按版本号排序（从新到旧）
        relevant_releases.sort(key=lambda r: self.parse_version(r['tag_name']), reverse=True)
        
        print(f"找到 {len(relevant_releases)} 个相关历史版本")
        return relevant_releases
    
    def truncate_release_body(self, body: str) -> str:
        """截断Release正文，移除构建信息等"""
        if not body:
            return ""
        
        body = body.strip()
        
        # 第一优先级：其他版本标题
        other_version_match = re.search(r'\n##\s+v?\d+\.\d+\.\d+', body)
        if other_version_match:
            return body[:other_version_match.start()].strip()
        
        # 第二优先级：CDK链接处理
        body = self.remove_duplicate_cdk_links(body)
        
        # 第三优先级：构建信息标记
        build_info_pattern = r'\n\*\*构建信息\*\*:'
        build_info_match = re.search(build_info_pattern, body)
        if build_info_match:
            return body[:build_info_match.start()].strip()
        
        # 保底策略：智能长度截断
        return self.smart_length_truncate(body)
    
    def remove_duplicate_cdk_links(self, body: str) -> str:
        """移除重复的CDK链接，只保留一个"""
        cdk_pattern = r'\[已有 Mirror酱 CDK[^\]]*\]\([^)]+\)'
        cdk_matches = list(re.finditer(cdk_pattern, body))
        
        if len(cdk_matches) <= 1:
            return body
        
        # 保留最后一个CDK链接
        last_cdk = cdk_matches[-1]
        result = body[:last_cdk.start()] + body[last_cdk.start():last_cdk.end()]
        
        return result.strip()
    
    def smart_length_truncate(self, body: str, max_lines: int = 50) -> str:
        """智能长度截断"""
        lines = body.split('\n')
        if len(lines) <= max_lines:
            return body
        
        # 找到合理的截断点（段落边界）
        for i in range(max_lines, 0, -1):
            if i < len(lines) and (lines[i].strip() == '' or lines[i].startswith('#')):
                return '\n'.join(lines[:i]).strip()
        
        # 实在找不到就在max_lines处硬截断
        return '\n'.join(lines[:max_lines]).strip() + "\n\n..."

def test_history_manager():
    """测试历史版本管理器"""
    print("=== 历史版本管理器测试 ===")
    
    # 需要设置环境变量
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    
    if not token or not repo:
        print("缺少环境变量，跳过测试")
        return
    
    repo_owner, repo_name = repo.split('/')
    manager = HistoryManager(token, repo_owner, repo_name)
    
    # 测试同次版本获取
    test_tag = "v2.3.6"
    historical_versions = manager.get_minor_version_series(test_tag)
    
    print(f"测试标签: {test_tag}")
    print(f"找到的历史版本: {[r['tag_name'] for r in historical_versions]}")

if __name__ == "__main__":
    test_history_manager()