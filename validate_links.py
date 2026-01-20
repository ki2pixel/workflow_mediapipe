#!/usr/bin/env python3
"""
Documentation Link Validator
Validates all cross-document anchors and links in the workflow documentation.
"""

import os
import re
import glob
from pathlib import Path
from urllib.parse import urlparse

class LinkValidator:
    def __init__(self, docs_dir):
        self.docs_dir = Path(docs_dir)
        self.markdown_files = list(self.docs_dir.glob("*.md"))
        self.issues = []

    def extract_links_from_markdown(self, content):
        """Extract all links from markdown content."""
        # Match markdown links: [text](url)
        markdown_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
        # Match bare URLs in text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        bare_urls = re.findall(url_pattern, content)

        return markdown_links, bare_urls

    def validate_internal_link(self, link_target, current_file):
        """Validate an internal link (relative path or anchor)."""
        if not link_target:
            return False, "Empty link target"

        # Check if it's an absolute URL
        if link_target.startswith(('http://', 'https://', 'ftp://')):
            return True, "External URL"

        # Check if it's a file reference
        if '.' in link_target and not link_target.startswith('#'):
            # Remove any fragment identifier
            file_part = link_target.split('#')[0]

            # Check if file exists
            if file_part.endswith('.md'):
                target_file = self.docs_dir / file_part
            else:
                # Assume .md extension
                target_file = self.docs_dir / f"{file_part}.md"

            if not target_file.exists():
                return False, f"File not found: {target_file.name}"

            # If there's an anchor, validate it exists in the file
            if '#' in link_target:
                anchor = link_target.split('#', 1)[1]
                if anchor:
                    target_content = target_file.read_text()
                    # Look for heading with this anchor
                    if f"id=\"{anchor}\"" not in target_content and f"#{anchor}" not in target_content:
                        # Try to find a heading that would generate this anchor
                        lines = target_content.split('\n')
                        for line in lines:
                            if line.strip().startswith('#'):
                                # Generate anchor from heading
                                heading_anchor = re.sub(r'[^\w\-_]', '', line.strip().lower().replace(' ', '-').replace('#', ''))
                                if heading_anchor == anchor:
                                    return True, f"Anchor found as heading: {line.strip()}"

                        return False, f"Anchor not found in {target_file.name}: #{anchor}"

        elif link_target.startswith('#'):
            # It's an anchor in the same file
            anchor = link_target[1:]
            if anchor:
                current_content = current_file.read_text()
                if f"id=\"{anchor}\"" not in current_content and f"#{anchor}" not in current_content:
                    return False, f"Anchor not found in current file: #{anchor}"

        return True, "Valid internal link"

    def validate_file(self, file_path):
        """Validate all links in a markdown file."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = file_path.read_text(encoding='latin-1')
            except:
                self.issues.append(f"Could not read file: {file_path.name}")
                return

        markdown_links, bare_urls = self.extract_links_from_markdown(content)

        for link_text, link_target in markdown_links:
            is_valid, message = self.validate_internal_link(link_target, file_path)
            if not is_valid:
                self.issues.append(f"[{file_path.name}] Broken link: {link_target} -> {message}")

        # Validate bare URLs (basic check)
        for url in bare_urls:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                self.issues.append(f"[{file_path.name}] Invalid URL format: {url}")

    def validate_all_files(self):
        """Validate all markdown files."""
        print(f"Validating {len(self.markdown_files)} markdown files...")

        for file_path in self.markdown_files:
            print(f"Checking {file_path.name}...")
            self.validate_file(file_path)

        self.print_report()

    def print_report(self):
        """Print validation report."""
        if not self.issues:
            print("\n✅ All links are valid!")
            return

        print(f"\n❌ Found {len(self.issues)} issues:")
        print("=" * 50)

        for issue in self.issues:
            print(f"• {issue}")

        print("=" * 50)

        # Group issues by type
        file_issues = [i for i in self.issues if "File not found" in i]
        anchor_issues = [i for i in self.issues if "Anchor not found" in i]
        url_issues = [i for i in self.issues if "Invalid URL" in i]

        print("\nSummary:")
        if file_issues:
            print(f"  🔗 File not found: {len(file_issues)}")
        if anchor_issues:
            print(f"  🎯 Anchor not found: {len(anchor_issues)}")
        if url_issues:
            print(f"  🌐 Invalid URLs: {len(url_issues)}")

def main():
    docs_dir = "/home/kidpixel/workflow_mediapipe/docs/workflow"
    validator = LinkValidator(docs_dir)
    validator.validate_all_files()

if __name__ == "__main__":
    main()
