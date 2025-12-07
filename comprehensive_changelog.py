#!/usr/bin/env python3
"""
综合变更日志生成脚本
自动合并同一次版本的所有正式版更新内容
"""

import os
import re
import requests
import logging
from typing import List, Dict, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChangelogGenerator:
    def __init__(self, current_tag: str, github_token: str, repo_owner: str, repo_name: str):
        self.current_tag = current_tag
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MFABD2-Changelog-Generator"
        }
    
    def get_all_releases(self) -> List[Dict]:
        """获取所有 releases"""
        logger.info("获取所有 releases...")
        url = f"{self.base_url}/releases"
        releases = []
        page = 1
        
        while True:
            response = requests.get(f"{url}?page={page}&per_page=100", headers=self.headers)
            if response.status_code != 200:
                logger.error(f"获取 releases 失败: {response.status_code} - {response.text}")
                break
            
            page_releases = response.json()
            if not page_releases:
                break
                
            releases.extend(page_releases)
            page += 1
            
            # 安全限制，最多获取10页
            if page > 10:
                logger.warning("达到页面限制，停止获取更多 releases")
                break
        
        logger.info(f"共获取 {len(releases)} 个 releases")
        return releases
    
    def is_formal_release(self, tag: str) -> bool:
        """判断是否为正式版标签"""
        return bool(re.match(r'^v\d+\.\d+\.\d+$', tag))
    
    def extract_minor_version(self, tag: str) -> Optional[str]:
        """从标签中提取次版本号"""
        match = re.match(r'^v(\d+\.\d+)\.\d+$', tag)
        return match.group(1) if match else None
    
    def extract_main_content(self, body: str) -> str:
        """提取主要内容（使用成功版本的逻辑）"""
        if not body:
            return ""
        
        # 方法1：查找标记 "## 历史版本更新内容"
        marker = "## 历史版本更新内容"
        marker_pos = body.find(marker)
        
        if marker_pos != -1:
            clean_content = body[:marker_pos].strip()
            logger.info("使用标记截断内容")
            return clean_content
        
        # 方法2：使用成功版本的正则表达式，移除固定结尾
        pattern = r'^(.*?)(?=\n\[已有 Mirror酱 CDK|\n*$)'
        match = re.search(pattern, body, re.DOTALL)
        content = match.group(1).strip() if match else body
        
        logger.info("使用CDK链接截断内容")
        return content
    
    def build_comprehensive_changelog(self) -> str:
        """构建完整的次版本变更历史（修复版本）"""
        
        # 提取次版本号（无论当前版本类型）
        minor_version = self.extract_minor_version(self.current_tag)
        if not minor_version:
            logger.info(f"无法从 {self.current_tag} 提取次版本号，跳过历史合并")
            return ""
        
        logger.info(f"查找次版本 {minor_version} 的所有正式版 Release...")
        
        # 获取所有 Release
        all_releases = self.get_all_releases()
        
        # 过滤出同一次版本的正式版 Release
        minor_releases = []
        for release in all_releases:
            tag = release['tag_name']
            if (self.is_formal_release(tag) and 
                self.extract_minor_version(tag) == minor_version and
                not release.get('prerelease', False)):
                minor_releases.append(release)
        
        if not minor_releases:
            logger.info(f"次版本 {minor_version} 没有正式版，无需合并历史")
            return ""
        
        # 按版本号排序（新版在上）
        minor_releases.sort(key=lambda x: [int(n) for n in x['tag_name'][1:].split('.')], reverse=True)
        
        logger.info(f"找到 {len(minor_releases)} 个正式版: {[r['tag_name'] for r in minor_releases]}")
        
        # 构建历史内容
        historical_content = ""
        for release in minor_releases:
            tag = release['tag_name']
            body = release.get('body', '') or ""
            published_at = release.get('published_at', '')[:10] if release.get('published_at') else "未知日期"
            
            main_content = self.extract_main_content(body)
            if not main_content.strip():
                logger.info(f"跳过版本 {tag}，内容为空")
                continue
                
            # 创建折叠块
            folded_block = f"""<details>
<summary>{tag} ({published_at}) 版本更新内容</summary>

{main_content}

</details>"""
            historical_content += folded_block + "\n\n"
            logger.info(f"为版本 {tag} 创建折叠块")
        
        if historical_content:
            final_content = f"""## 历史版本更新内容

{historical_content}"""
            logger.info(f"生成历史区块，包含 {len(minor_releases)} 个版本")
            return final_content
        else:
            logger.info("没有生成历史内容")
            return ""
    
    def merge_into_current_changelog(self, current_content: str, historical_section: str) -> str:
        """将历史区块合并到当前 changelog（保持现有逻辑）"""
        if not historical_section:
            logger.info("没有历史区块，返回原始内容")
            return current_content
        
        # 查找构建信息的开始位置
        build_info_marker = "**构建信息**:"
        build_info_pos = current_content.find(build_info_marker)
        
        if build_info_pos != -1:
            # 找到构建信息的末尾
            insert_pos = current_content.find('\n', build_info_pos)
            while insert_pos != -1 and insert_pos < len(current_content) - 1:
                next_chars = current_content[insert_pos:insert_pos+10]
                if next_chars.strip() == "" or next_chars.startswith('\n##'):
                    break
                insert_pos = current_content.find('\n', insert_pos + 1)
            
            if insert_pos == -1:
                insert_pos = len(current_content)
            
            logger.info(f"在构建信息后插入历史区块")
            return (current_content[:insert_pos] + 
                    "\n\n" + historical_section + 
                    current_content[insert_pos:])
        else:
            # 如果没有构建信息，在CDK链接后插入
            cdk_marker = "[已有 Mirror酱 CDK"
            cdk_pos = current_content.find(cdk_marker)
            
            if cdk_pos != -1:
                cdk_end = current_content.find('\n', cdk_pos)
                if cdk_end == -1:
                    cdk_end = len(current_content)
                
                logger.info(f"在CDK链接后插入历史区块")
                return (current_content[:cdk_end] + 
                        "\n\n" + historical_section + 
                        current_content[cdk_end:])
            else:
                logger.info("在末尾插入历史区块")
                return current_content + "\n\n" + historical_section
    
    def generate_comprehensive_changelog(self) -> str:
        """生成完整的 changelog"""
        logger.info("开始生成完整 changelog")
        
        # 读取当前生成的 changelog
        try:
            with open('current_changelog.md', 'r', encoding='utf-8') as f:
                current_content = f.read()
            logger.info(f"读取当前 changelog，长度: {len(current_content)}")
        except FileNotFoundError:
            logger.error("找不到 current_changelog.md 文件")
            return ""
        
        # 生成历史内容
        historical_section = self.build_comprehensive_changelog()
        
        # 合并到当前内容
        final_content = self.merge_into_current_changelog(current_content, historical_section)
        
        logger.info("完整 changelog 生成完成")
        return final_content

def main():
    # 从环境变量获取参数
    current_tag = os.environ.get('CURRENT_TAG')
    github_token = os.environ.get('GITHUB_TOKEN')
    github_repository = os.environ.get('GITHUB_REPOSITORY')
    github_repository_owner = os.environ.get('GITHUB_REPOSITORY_OWNER')
    
    if not all([current_tag, github_token, github_repository]):
        logger.error("缺少必要的环境变量")
        return 1
    
    # 解析仓库信息
    repo_parts = github_repository.split('/')
    if len(repo_parts) != 2:
        logger.error(f"无效的仓库名称: {github_repository}")
        return 1
    
    repo_owner = repo_parts[0]
    repo_name = repo_parts[1]
    
    logger.info(f"开始处理: 仓库={github_repository}, 版本={current_tag}")
    
    # 生成完整 changelog
    generator = ChangelogGenerator(current_tag, github_token, repo_owner, repo_name)
    final_content = generator.generate_comprehensive_changelog()
    
    # 写入最终文件
    if final_content:
        with open('CHANGES.md', 'w', encoding='utf-8') as f:
            f.write(final_content)
        logger.info("CHANGES.md 写入成功")
    else:
        logger.error("生成 changelog 失败")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())