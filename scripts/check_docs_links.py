#!/usr/bin/env python3
"""
Script to verify internal links in Markdown documentation.
Checks for broken internal links after the documentation reorganization.
"""

import os
import re
import sys
from pathlib import Path

# Define the project root and docs directory
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / 'docs'

# Pattern to match Markdown links: [text](url)
LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# Pattern to match anchor links: #some-anchor
ANCHOR_PATTERN = re.compile(r'^#.+$')

# Pattern to match external URLs (http(s):// or mailto:)
EXTERNAL_PATTERN = re.compile(r'^(https?://|mailto:)')

def is_valid_anchor(file_path, anchor):
    """Check if an anchor exists in the given file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for headers that would create this anchor
            # Convert anchor to header text (simplified)
            header_text = anchor[1:].replace('-', ' ').title()
            return f'# {header_text}' in content or f'## {header_text}' in content
    except Exception as e:
        print(f"Error checking anchor in {file_path}: {e}")
        return False

def check_links():
    """Check all Markdown files in the docs directory for broken links."""
    issues_found = False
    
    # Get all Markdown files in the docs directory
    md_files = list(DOCS_DIR.glob('**/*.md'))
    
    for md_file in md_files:
        print(f"\nChecking links in: {md_file.relative_to(PROJECT_ROOT)}")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for match in LINK_PATTERN.finditer(content):
                link_text = match.group(1)
                link_url = match.group(2)
                
                # Skip external links
                if EXTERNAL_PATTERN.match(link_url):
                    continue
                    
                # Handle anchor-only links (#section)
                if ANCHOR_PATTERN.match(link_url):
                    if not is_valid_anchor(md_file, link_url):
                        print(f"  ❌ Broken anchor link: {link_url} (in {md_file.name} -> {link_text})")
                        issues_found = True
                    continue
                
                # Handle relative links
                if '#' in link_url:
                    file_part, anchor_part = link_url.split('#', 1)
                else:
                    file_part = link_url
                    anchor_part = None
                
                # Handle empty file part (just an anchor)
                if not file_part:
                    if not is_valid_anchor(md_file, '#' + anchor_part):
                        print(f"  ❌ Broken anchor link: #{anchor_part} (in {md_file.name} -> {link_text})")
                        issues_found = True
                    continue
                
                # Resolve the target file path
                target_path = (md_file.parent / file_part).resolve()
                
                # Check if the target file exists
                if not target_path.exists():
                    print(f"  ❌ Broken link: {link_url} (in {md_file.name} -> {link_text})")
                    print(f"     File not found: {target_path}")
                    issues_found = True
                    continue
                    
                # If there's an anchor, check it exists in the target file
                if anchor_part and not is_valid_anchor(target_path, '#' + anchor_part):
                    print(f"  ❌ Broken anchor in {link_url} (in {md_file.name} -> {link_text})")
                    print(f"     Anchor not found in: {target_path.relative_to(PROJECT_ROOT)}")
                    issues_found = True
        
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
            issues_found = True
    
    return issues_found

if __name__ == "__main__":
    print("Checking documentation links...")
    if check_links():
        print("\n❌ Issues found with documentation links. Please fix them before release.")
        sys.exit(1)
    else:
        print("\n✅ All documentation links are valid!")
