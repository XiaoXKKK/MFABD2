#!/usr/bin/env python3
"""
主入口 - 协调整个变更日志生成流程
"""

import os
import sys
from typing import List, Dict
from version_logic import calculate_compare_base
from git_operations import get_commit_list
from version_rules import filter_valid_versions, sort_versions

def group_commits_by_type(commits: List[Dict]) -> Dict[str, List[Dict]]:
    """按提交类型分组（简化版本，后续可以改进）"""
    groups = {
        'feat': [],
        'fix': [], 
        'docs': [],
        'style': [],
        'refactor': [],
        'test': [],
        'chore': [],
        'other': []
    }
    
    for commit in commits:
        subject = commit['subject'].lower()
        
        if subject.startswith('feat'):
            groups['feat'].append(commit)
        elif subject.startswith('fix'):
            groups['fix'].append(commit)
        elif subject.startswith('docs'):
            groups['docs'].append(commit)
        elif subject.startswith('style'):
            groups['style'].append(commit)
        elif subject.startswith('refactor'):
            groups['refactor'].append(commit)
        elif subject.startswith('test'):
            groups['test'].append(commit)
        elif subject.startswith('chore'):
            groups['chore'].append(commit)
        else:
            groups['other'].append(commit)
    
    return groups

def format_commit_message(commit: Dict) -> str:
    """格式化单个提交信息"""
    subject = commit['subject']
    author = commit['author_name']
    
    # 移除类型前缀，让消息更可读
    if ': ' in subject:
        message = subject.split(': ', 1)[1]
    else:
        message = subject
    
    return f"- {message} @{author}"

def generate_changelog_content(commits: List[Dict], current_tag: str, compare_base: str) -> str:
    """生成变更日志内容"""
    
    if not commits:
        return f"# 更新日志\n\n## {current_tag}\n\n*无显著变更*\n"
    
    grouped_commits = group_commits_by_type(commits)
    
    # 构建变更日志
    changelog = f"# 更新日志\n\n"
    changelog += f"## {current_tag}\n\n"
    
    # 定义分组标题
    group_titles = {
        'feat': '✨ 新功能',
        'fix': '🐛 Bug修复', 
        'docs': '📚 文档',
        'style': '🎨 样式',
        'refactor': '🚜 代码重构',
        'test': '🧪 测试',
        'chore': '🔧 日常维护',
        'other': '其他变更'
    }
    
    # 输出有内容的分组
    for group_type, title in group_titles.items():
        group_commits = grouped_commits[group_type]
        if group_commits:
            changelog += f"### {title}\n\n"
            for commit in group_commits:
                changelog += format_commit_message(commit) + "\n"
            changelog += "\n"
    
    changelog += f"**对比范围**: {compare_base}..{current_tag}\n"
    
    return changelog

def main():
    """主函数"""
    print("=== 变更日志生成器 ===\n")
    
    # 获取当前标签（从环境变量或参数）
    current_tag = os.environ.get('CURRENT_TAG')
    if not current_tag:
        # 如果没有环境变量，使用测试标签
        current_tag = "v2.3.5"
        print(f"使用测试标签: {current_tag}")
    else:
        print(f"使用环境变量标签: {current_tag}")
    
    # 计算对比基准
    print("计算对比基准...")
    compare_base = calculate_compare_base(current_tag)
    print(f"对比基准: {compare_base}")
    
    # 获取提交列表
    print("获取提交列表...")
    commits = get_commit_list(compare_base, current_tag)
    print(f"获取到 {len(commits)} 个提交")
    
    # 生成变更日志
    print("生成变更日志...")
    changelog_content = generate_changelog_content(commits, current_tag, compare_base)
    
    # 输出到文件
    output_file = "../CHANGES.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(changelog_content)
    
    print(f"✅ 变更日志已生成: {output_file}")
    
    # 显示预览
    print("\n=== 变更日志预览 ===")
    lines = changelog_content.split('\n')
    for line in lines[:20]:  # 显示前20行
        print(line)
    
    if len(lines) > 20:
        print("... (完整内容请查看 CHANGES.md 文件)")

def test_changelog_generator():
    """测试变更日志生成器"""
    print("=== 变更日志生成器测试 ===\n")
    
    test_cases = [
        "v2.3.5",      # 正式版
        "v2.3.4",      # 另一个正式版
    ]
    
    for test_tag in test_cases:
        print(f"测试标签: {test_tag}")
        print("-" * 40)
        
        compare_base = calculate_compare_base(test_tag)
        commits = get_commit_list(compare_base, test_tag)
        
        print(f"对比基准: {compare_base}")
        print(f"提交数量: {len(commits)}")  # ✅ 修复：添加了引号
        print()

if __name__ == "__main__":
    # 测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_changelog_generator()
    else:
        # 正常模式
        main()