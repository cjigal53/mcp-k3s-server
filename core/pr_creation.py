"""PR Creation module for handling pull request operations.

This module provides utilities for creating and managing pull requests
programmatically.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PRData:
    """Data class representing a Pull Request.
    
    Attributes:
        title: The title of the pull request.
        body: The description/body of the pull request.
        branch: The source branch for the PR.
        base: The target branch (default: main).
        labels: Optional list of labels to apply.
        issue_number: Optional issue number this PR addresses.
    """
    
    title: str
    body: str
    branch: str
    base: str = "main"
    labels: Optional[List[str]] = None
    issue_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert PRData to dictionary format.
        
        Returns:
            Dictionary representation of the PR data.
        """
        data: Dict[str, Any] = {
            "title": self.title,
            "body": self.body,
            "head": self.branch,
            "base": self.base,
        }
        if self.labels:
            data["labels"] = self.labels
        return data


class PRCreationHandler:
    """Handler for PR creation operations."""

    def __init__(self, repository: str) -> None:
        """Initialize the PR creation handler.
        
        Args:
            repository: The repository in 'owner/repo' format.
        """
        self.repository = repository

    def validate_pr_data(self, pr_data: PRData) -> bool:
        """Validate PR data before creation.
        
        Args:
            pr_data: The PR data to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not pr_data.title or not pr_data.title.strip():
            return False
        if not pr_data.body or not pr_data.body.strip():
            return False
        if not pr_data.branch or not pr_data.branch.strip():
            return False
        return True

    def format_branch_name(self, issue_number: int, description: str) -> str:
        """Format a branch name following conventions.
        
        Args:
            issue_number: The issue number being addressed.
            description: Short description for the branch.
            
        Returns:
            Formatted branch name.
        """
        # Clean description: lowercase, replace spaces with hyphens
        clean_description = description.lower().replace(" ", "-")
        # Remove any characters that aren't alphanumeric or hyphens
        clean_description = "".join(
            c for c in clean_description if c.isalnum() or c == "-"
        )
        return f"feature/issue-{issue_number}-{clean_description}"

    def create_pr_body(self, issue_number: int, description: str) -> str:
        """Create a standardized PR body.
        
        Args:
            issue_number: The issue number being addressed.
            description: Description of the changes.
            
        Returns:
            Formatted PR body string.
        """
        return f"""## Summary

Fixes #{issue_number}

## Description

{description}

## Checklist

- [x] Code follows project style guidelines
- [x] Tests added/updated as needed
- [x] Documentation updated as needed
"""

    def prepare_pr(self, issue_number: int, title: str, description: str) -> PRData:
        """Prepare PR data for creation.
        
        Args:
            issue_number: The issue number being addressed.
            title: The PR title.
            description: Description of the changes.
            
        Returns:
            PRData instance ready for creation.
        """
        branch = self.format_branch_name(issue_number, title)
        body = self.create_pr_body(issue_number, description)
        
        return PRData(
            title=title,
            body=body,
            branch=branch,
            base="main",
            labels=["auto-generated"],
            issue_number=issue_number,
        )
