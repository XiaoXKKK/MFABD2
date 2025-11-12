#!/usr/bin/env python3
"""
版本规则 - 严格的版本过滤和分类
"""

import re
from typing import List, Dict  # ✅ 确保有这些导入


def is_valid_formal_version(tag: str) -> bool:
    """判断是否为有效的正式版 - 严格模式"""
    # 严格的正式版模式：v数字.数字.数字，从v2.0.0开始
    if not re.match(r'^v\d+\.\d+\.\d+$', tag):
        return False
    
    # 只接受v2.0.0及以上的正式版，忽略所有v0.x.x和v1.x.x
    if tag.startswith(('v0.', 'v1.')):
        return False
        
    return True

def is_valid_beta_version(tag: str) -> bool:
    """判断是否为有效的内测版 - 严格模式"""
    # 必须符合: v数字.数字.数字-beta.6位日期.7位以上哈希
    pattern = r'^v\d+\.\d+\.\d+-beta\.\d{6}\.[a-f0-9]{7,}$'
    return bool(re.match(pattern, tag))

def is_valid_ci_version(tag: str) -> bool:
    """判断是否为有效的开发版 - 严格模式"""
    # 必须符合: v数字.数字.数字-ci.6位日期.7位以上哈希
    pattern = r'^v\d+\.\d+\.\d+-ci\.\d{6}\.[a-f0-9]{7,}$'
    return bool(re.match(pattern, tag))

def is_nested_version(tag: str) -> bool:
    """检测是否为嵌套版本（需要排除的错误版本）"""
    # 检测包含多个-beta或-ci的嵌套版本
    beta_count = tag.count('-beta')
    ci_count = tag.count('-ci')
    return (beta_count + ci_count) > 1

def filter_valid_versions(tags: List[str]) -> Dict[str, List[str]]:
    """严格过滤有效的版本"""
    result = {
        'formal': [],    # 正式版
        'beta': [],      # 内测版  
        'ci': [],        # 开发版
        'invalid': [],   # 无效版本
        'nested': []     # 嵌套错误版本
    }
    
    for tag in tags:
        # 首先检查是否为嵌套版本（最高优先级排除）
        if is_nested_version(tag):
            result['nested'].append(tag)
            continue
            
        # 然后检查其他有效版本
        if is_valid_formal_version(tag):
            result['formal'].append(tag)
        elif is_valid_beta_version(tag):
            result['beta'].append(tag)
        elif is_valid_ci_version(tag):
            result['ci'].append(tag)
        else:
            result['invalid'].append(tag)
    
    return result

def sort_versions(versions: List[str]) -> List[str]:
    """按版本号排序（从新到旧）"""
    def version_key(tag):
        # 提取版本号部分进行排序（支持内测版/开发版）
        try:
            base_tag = re.sub(r'(-beta\.\d+\.[a-f0-9]+|-ci\.\d+\.[a-f0-9]+)$', '', tag)
            numbers = base_tag[1:].split('.')  # 去掉'v'，按.分割
            return [int(num) for num in numbers]
        except Exception as e:
            print(f"版本排序警告: {tag} - {e}")
            return [0, 0, 0]  # 返回默认值避免崩溃
    
    return sorted(versions, key=version_key, reverse=True)

if __name__ == "__main__":
    # 测试代码
    test_tags = [
        "v2.3.6",                           # 有效正式版
        "v2.3.6-beta.251111.c7b2aa3",       # 有效内测版  
        "v2.3.6-ci.251111.abc1234",         # 有效开发版
        "v2.4.0-beta",                      # 无效：缺少日期和哈希
        "v0.1000.1",                        # 无效：v0.x.x
        "vdev100.1",                        # 无效：非标准格式
        "v2.3.7-beta.251110.38e6ace-ci.251110.72b3fe3",  # 嵌套版本
    ]
    
    print("=== 版本过滤测试 ===")
    filtered = filter_valid_versions(test_tags)
    
    for category, tags in filtered.items():
        print(f"\n{category.upper()} ({len(tags)}个):")
        for tag in tags:
            print(f"  - {tag}")
    
    # 显示排序后的正式版
    if filtered['formal']:
        sorted_formal = sort_versions(filtered['formal'])
        print(f"\n排序后的正式版（从新到旧）:")
        for tag in sorted_formal:
            print(f"  - {tag}")