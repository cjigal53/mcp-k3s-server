"""Utility functions for PR operations.

This module provides helper functions for working with pull requests.
"""

from typing import List, Optional
import re


def extract_issue_numbers(text: str) -> List[int]:
    """Extract issue numbers from text.
    
    Args:
        text: Text that may contain issue references like #123.
        
    Returns:
        List of issue numbers found.
    """
    pattern = r"#(\d+)"
    matches = re.findall(pattern, text)
    return [int(m) for m in matches]


def sanitize_branch_name(name: str) -> str:
    """Sanitize a string for use as a branch name.
    
    Args:
        name: The raw name to sanitize.
        
    Returns:
        Sanitized branch name.
    """
    # Convert to lowercase
    sanitized = name.lower()
    # Replace spaces and underscores with hyphens
    sanitized = re.sub(r"[\s_]+", "-", sanitized)
    # Remove any character that isn't alphanumeric or hyphen
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    # Remove consecutive hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")
    return sanitized


def format_pr_title(issue_number: int, description: str) -> str:
    """Format a PR title with issue reference.
    
    Args:
        issue_number: The issue number being addressed.
        description: Short description of the PR.
        
    Returns:
        Formatted PR title.
    """
    return f"[#{issue_number}] {description}"


def validate_repository_format(repository: str) -> bool:
    """Validate repository string format.
    
    Args:
        repository: Repository string to validate (owner/repo format).
        
    Returns:
        True if valid, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"
    return bool(re.match(pattern, repository))


def get_closing_keywords() -> List[str]:
    """Get list of keywords that close issues when PR is merged.
    
    Returns:
        List of closing keywords.
    """
    return [
        "close",
        "closes",
        "closed",
        "fix",
        "fixes",
        "fixed",
        "resolve",
        "resolves",
        "resolved",
    ]


def create_closing_reference(issue_number: int, keyword: str = "Fixes") -> str:
    """Create a closing reference for an issue.
    
    Args:
        issue_number: The issue number to reference.
        keyword: The closing keyword to use (default: Fixes).
        
    Returns:
        Closing reference string.
    """
    return f"{keyword} #{issue_number}"
