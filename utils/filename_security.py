#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive filename sanitization and security utilities for archive extraction.
Provides secure filename handling to prevent filesystem attacks and ensure compatibility.
"""

import os
import re
import unicodedata
import logging
from pathlib import Path
from typing import Tuple, Set, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WINDOWS_FORBIDDEN_CHARS = set('<>:"|?*')
UNIX_FORBIDDEN_CHARS = set('\x00')  # Null byte
CONTROL_CHARS = set(chr(i) for i in range(32))  # ASCII control characters
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

MAX_FILENAME_LENGTH = 255
MAX_PATH_LENGTH = 4096
MAX_COMPONENT_LENGTH = 255

DANGEROUS_PATTERNS = [
    r'\.\.[\\/]',  # Path traversal
    r'^[\\/]',     # Absolute paths
    r'[\\/]\.\.[\\/]',  # Path traversal in middle
    r'[\\/]\.\.$',      # Path traversal at end
]


@dataclass
class SanitizationResult:
    """Result of filename sanitization operation."""
    original_name: str
    sanitized_name: str
    was_modified: bool
    security_issues: List[str]
    warnings: List[str]


class FilenameSanitizer:
    """
    Comprehensive filename sanitizer for secure archive extraction.
    
    Handles:
    - Path traversal prevention
    - Platform-specific forbidden characters
    - Unicode normalization
    - Length limits
    - Reserved names
    - Control character filtering
    """
    
    def __init__(self, max_filename_length: int = MAX_FILENAME_LENGTH):
        """
        Initialize the sanitizer.
        
        Args:
            max_filename_length: Maximum allowed filename length
        """
        self.max_filename_length = max_filename_length
        self.sanitization_stats = {
            'total_processed': 0,
            'modified_count': 0,
            'security_issues_found': 0
        }
    
    def sanitize_archive_member_path(self, member_path: str) -> SanitizationResult:
        """
        Sanitize a complete path from an archive member.
        
        Args:
            member_path: Original path from archive
            
        Returns:
            SanitizationResult with sanitized path and security info
        """
        self.sanitization_stats['total_processed'] += 1
        original_path = member_path
        security_issues = []
        warnings = []
        
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, member_path):
                security_issues.append(f"Path traversal pattern detected: {pattern}")
        
        member_path = unicodedata.normalize('NFKC', member_path)
        
        path_parts = []
        for part in member_path.split('/'):
            if part in ('', '.', '..'):
                security_issues.append(f"Dangerous path component: '{part}'")
                continue
            
            sanitized_part = self._sanitize_filename_component(part)
            if sanitized_part.was_modified:
                warnings.extend(sanitized_part.warnings)
                security_issues.extend(sanitized_part.security_issues)
            
            if sanitized_part.sanitized_name:  # Only add non-empty parts
                path_parts.append(sanitized_part.sanitized_name)
        
        sanitized_path = '/'.join(path_parts) if path_parts else 'sanitized_file'
        
        if len(sanitized_path) > MAX_PATH_LENGTH:
            warnings.append(f"Path length {len(sanitized_path)} exceeds limit {MAX_PATH_LENGTH}")
            sanitized_path = self._truncate_path(sanitized_path)
        
        was_modified = original_path != sanitized_path
        if was_modified:
            self.sanitization_stats['modified_count'] += 1
        
        if security_issues:
            self.sanitization_stats['security_issues_found'] += 1
            logger.warning(f"Security issues in path '{original_path}': {security_issues}")
        
        return SanitizationResult(
            original_name=original_path,
            sanitized_name=sanitized_path,
            was_modified=was_modified,
            security_issues=security_issues,
            warnings=warnings
        )
    
    def _sanitize_filename_component(self, filename: str) -> SanitizationResult:
        """
        Sanitize a single filename component.
        
        Args:
            filename: Original filename
            
        Returns:
            SanitizationResult with sanitized filename and security info
        """
        original_filename = filename
        security_issues = []
        warnings = []
        
        for char in CONTROL_CHARS | UNIX_FORBIDDEN_CHARS:
            if char in filename:
                security_issues.append(f"Control/null character detected: {repr(char)}")
                filename = filename.replace(char, '')
        
        for char in WINDOWS_FORBIDDEN_CHARS:
            if char in filename:
                warnings.append(f"Windows forbidden character replaced: '{char}'")
                filename = filename.replace(char, '_')
        
        original_stripped = filename
        filename = filename.strip('. ')
        if filename != original_stripped:
            warnings.append("Removed leading/trailing dots or spaces")
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in WINDOWS_RESERVED_NAMES:
            security_issues.append(f"Windows reserved name detected: {name_without_ext}")
            filename = f"safe_{filename}"
        
        if len(filename) > self.max_filename_length:
            warnings.append(f"Filename length {len(filename)} exceeds limit {self.max_filename_length}")
            filename = self._truncate_filename(filename)
        
        if not filename or filename in ('.', '..'):
            warnings.append("Empty or invalid filename, using fallback")
            filename = 'sanitized_file'
        
        was_modified = original_filename != filename
        
        return SanitizationResult(
            original_name=original_filename,
            sanitized_name=filename,
            was_modified=was_modified,
            security_issues=security_issues,
            warnings=warnings
        )
    
    def _truncate_filename(self, filename: str) -> str:
        """
        Truncate filename while preserving extension.
        
        Args:
            filename: Filename to truncate
            
        Returns:
            Truncated filename
        """
        if len(filename) <= self.max_filename_length:
            return filename
        
        path_obj = Path(filename)
        extension = path_obj.suffix
        name_part = path_obj.stem
        
        max_name_length = self.max_filename_length - len(extension)
        
        if max_name_length <= 0:
            return filename[:self.max_filename_length]
        
        truncated_name = name_part[:max_name_length]
        return truncated_name + extension
    
    def _truncate_path(self, path: str) -> str:
        """
        Truncate path while preserving structure.
        
        Args:
            path: Path to truncate
            
        Returns:
            Truncated path
        """
        if len(path) <= MAX_PATH_LENGTH:
            return path
        
        excess = len(path) - MAX_PATH_LENGTH + 10  # +10 for "..." marker
        middle = len(path) // 2
        start = middle - excess // 2
        end = middle + excess // 2
        
        return path[:start] + "..." + path[end:]
    
    def get_stats(self) -> dict:
        """Get sanitization statistics."""
        return self.sanitization_stats.copy()
    
    def reset_stats(self):
        """Reset sanitization statistics."""
        self.sanitization_stats = {
            'total_processed': 0,
            'modified_count': 0,
            'security_issues_found': 0
        }


def validate_extraction_path(member_path: str, base_extraction_dir: Path) -> bool:
    """
    Validate that an extraction path is safe relative to base directory.
    
    Args:
        member_path: Path from archive member
        base_extraction_dir: Base directory for extraction
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        full_path = (base_extraction_dir / member_path).resolve()
        base_resolved = base_extraction_dir.resolve()
        
        try:
            full_path.relative_to(base_resolved)
            return True
        except ValueError:
            logger.warning(f"Path outside base directory: {member_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error validating extraction path '{member_path}': {e}")
        return False


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Simple filename sanitization function.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename
    """
    sanitizer = FilenameSanitizer(max_length)
    result = sanitizer._sanitize_filename_component(filename)
    return result.sanitized_name
