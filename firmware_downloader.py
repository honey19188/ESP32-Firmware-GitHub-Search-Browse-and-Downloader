#!/usr/bin/env python3
"""
ESP32 Firmware Downloader - 通过查询 GitHub 下载 ESP32 固件的工具
"""

import argparse
import os
import sys
import requests
from pathlib import Path


GITHUB_API_URL = "https://api.github.com"
DEFAULT_OUTPUT_DIR = "firmware_downloads"


def search_firmware_repos(query: str, max_results: int = 10):
    """搜索 GitHub 上的 ESP32 固件仓库"""
    url = f"{GITHUB_API_URL}/search/repositories"
    params = {
        "q": f"{query} esp32 firmware",
        "per_page": max_results,
        "sort": "stars",
        "order": "desc"
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    return data.get("items", [])


def get_releases(owner: str, repo: str):
    """获取仓库的所有 releases"""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_release_assets(owner: str, repo: str, tag_name: str):
    """获取特定 release 的所有资产文件"""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases/tags/{tag_name}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("assets", [])


def download_file(url: str, destination: Path, chunk_size: int = 8192):
    """下载文件到指定目录"""
    print(f"正在下载: {url}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r进度: {percent:.1f}%", end="", flush=True)
    
    print()
    return destination


def parse_github_url(url: str):
    """解析 GitHub URL 或 owner/repo 格式"""
    url = url.strip()
    
    # 处理完整 URL
    if "github.com" in url:
        parts = url.rstrip("/").split("/")
        # 过滤掉空字符串和 'repositories'
        parts = [p for p in parts if p and p != "repositories"]
        if len(parts) >= 2:
            return parts[-2], parts[-1].split(".")[0]  # owner, repo
    
    # 处理 owner/repo 格式
    if "/" in url:
        parts = url.split("/")
        if len(parts) == 2:
            return parts[0], parts[1].split(".")[0]
    
    return None, None


def list_firmware(args):
    """列出搜索到的固件仓库或指定仓库的 releases"""
    if args.repo:
        owner, repo = parse_github_url(args.repo)
        if not owner or not repo:
            print("无效的仓库地址")
            return
        
        print(f"\n仓库: {owner}/{repo}\n")
        try:
            releases = get_releases(owner, repo)
            if not releases:
                print("没有找到 releases")
                return
            
            for i, release in enumerate(releases, 1):
                print(f"{i}. {release['tag_name']}")
                print(f"   标题: {release.get('name', 'N/A')}")
                print(f"   发布日期: {release.get('published_at', 'N/A')[:10]}")
                print(f"   预发布: {'是' if release.get('prerelease') else '否'}")
                assets = release.get("assets", [])
                if assets:
                    print(f"   资产文件: {len(assets)} 个")
                    for asset in assets:
                        print(f"      - {asset['name']} ({asset.get('size', 0) / 1024:.1f} KB)")
                print()
        except requests.exceptions.HTTPError as e:
            print(f"获取 releases 失败: {e}")
    else:
        print(f"\n搜索关键词: {args.query}\n")
        repos = search_firmware_repos(args.query, args.max_results)
        
        if not repos:
            print("没有找到匹配的仓库")
            return
        
        for i, repo in enumerate(repos, 1):
            print(f"{i}. {repo['full_name']}")
            print(f"   星标: {repo['stargazers_count']}")
            print(f"   描述: {repo.get('description', 'N/A')}")
            print(f"   地址: {repo['html_url']}")
            print()


def download_firmware(args):
    """下载固件"""
    owner, repo = parse_github_url(args.repo)
    if not owner or not repo:
        print("无效的仓库地址")
        return
    
    output_dir = Path(args.output or DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if args.tag:
            # 下载指定 tag 的所有资产或指定文件
            assets = get_release_assets(owner, repo, args.tag)
            if not assets:
                print(f"Tag '{args.tag}' 没有找到资产文件")
                return
            
            downloaded_count = 0
            for asset in assets:
                if args.file and args.file != asset["name"]:
                    continue
                
                download_url = asset["browser_download_url"]
                destination = output_dir / asset["name"]
                download_file(download_url, destination)
                downloaded_count += 1
            
            if downloaded_count == 0:
                print("没有找到匹配的文件")
        else:
            # 获取最新 release
            releases = get_releases(owner, repo)
            if not releases:
                print("没有找到 releases")
                return
            
            latest = releases[0]
            print(f"最新版本: {latest['tag_name']}")
            print(f"标题: {latest.get('name', 'N/A')}\n")
            
            assets = latest.get("assets", [])
            if not assets:
                print("该 release 没有资产文件")
                return
            
            downloaded_count = 0
            for asset in assets:
                if args.file and args.file != asset["name"]:
                    continue
                
                download_url = asset["browser_download_url"]
                destination = output_dir / asset["name"]
                download_file(download_url, destination)
                downloaded_count += 1
            
            if downloaded_count == 0 and args.file:
                print("没有找到匹配的文件")
            
            print(f"\n下载完成! 文件保存在: {output_dir.absolute()}")
            
    except requests.exceptions.HTTPError as e:
        print(f"下载失败: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 固件下载工具 - 从 GitHub 查询和下载 ESP32 固件",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出固件仓库或 releases")
    list_parser.add_argument("-q", "--query", default="esp32-firmware", help="搜索关键词 (默认: esp32-firmware)")
    list_parser.add_argument("-n", "--max-results", type=int, default=10, help="最大结果数")
    list_parser.add_argument("-r", "--repo", help="指定仓库，列出其 releases (格式: owner/repo 或 GitHub URL)")
    list_parser.set_defaults(func=list_firmware)
    
    # download 命令
    download_parser = subparsers.add_parser("download", help="下载固件")
    download_parser.add_argument("repo", help="仓库地址 (格式: owner/repo 或 GitHub URL)")
    download_parser.add_argument("-t", "--tag", help="指定版本标签")
    download_parser.add_argument("-f", "--file", help="指定要下载的文件名")
    download_parser.add_argument("-o", "--output", help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})")
    download_parser.set_defaults(func=download_firmware)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
