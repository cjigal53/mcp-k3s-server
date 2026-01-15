"""PR Manager module for handling pull request operations.

This module provides functionality for creating and managing pull requests,
with proper async/await handling to prevent coroutine warnings.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class FileChange:
    """Represents a file change for a pull request.
    
    Attributes:
        path: The file path relative to repository root.
        operation: The type of operation ('create', 'modify', 'delete').
        content: The file content (empty for delete operations).
    """
    path: str
    operation: str
    content: str = ""


@dataclass
class PRData:
    """Data structure for pull request creation.
    
    Attributes:
        title: The PR title.
        body: The PR description body.
        head: The source branch name.
        base: The target branch name.
        issue_number: The related issue number (optional).
    """
    title: str
    body: str
    head: str
    base: str = "main"
    issue_number: Optional[int] = None


class PRManager:
    """Manager class for pull request operations.
    
    This class handles the creation and management of pull requests,
    with proper async/await handling to prevent coroutine warnings.
    
    Attributes:
        github_client: The GitHub API client instance.
        repository: The target repository name.
    """
    
    def __init__(
        self,
        github_client: Optional[Any] = None,
        repository: Optional[str] = None
    ) -> None:
        """Initialize the PR Manager.
        
        Args:
            github_client: The GitHub API client instance.
            repository: The target repository name.
        """
        self.github_client = github_client
        self.repository = repository
    
    async def create_branch(self, branch_name: str, base_ref: str = "main") -> Dict[str, Any]:
        """Create a new branch for the pull request.
        
        Args:
            branch_name: The name of the new branch.
            base_ref: The base reference to create the branch from.
            
        Returns:
            A dictionary containing the branch creation result.
        """
        # Simulate async branch creation
        await asyncio.sleep(0)  # Yield control to event loop
        return {
            "branch": branch_name,
            "base": base_ref,
            "status": "created",
        }
    
    async def commit_changes(
        self,
        branch_name: str,
        file_changes: List[FileChange],
        commit_message: str
    ) -> Dict[str, Any]:
        """Commit file changes to a branch.
        
        Args:
            branch_name: The target branch name.
            file_changes: List of file changes to commit.
            commit_message: The commit message.
            
        Returns:
            A dictionary containing the commit result.
        """
        await asyncio.sleep(0)  # Yield control to event loop
        return {
            "branch": branch_name,
            "files_changed": len(file_changes),
            "message": commit_message,
            "status": "committed",
        }
    
    async def create_pull_request(self, pr_data: PRData) -> Dict[str, Any]:
        """Create a pull request.
        
        This method properly handles async operations to prevent
        'coroutine was never awaited' warnings.
        
        Args:
            pr_data: The pull request data.
            
        Returns:
            A dictionary containing the PR creation result.
        """
        await asyncio.sleep(0)  # Yield control to event loop
        
        result: Dict[str, Any] = {
            "title": pr_data.title,
            "body": pr_data.body,
            "head": pr_data.head,
            "base": pr_data.base,
            "status": "created",
            "pr_number": pr_data.issue_number or 1,
        }
        
        return result
    
    async def create_pr_from_changes(
        self,
        issue_number: int,
        title: str,
        body: str,
        file_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a complete PR from file changes.
        
        This is the main entry point for PR creation, handling
        the complete workflow from branch creation to PR submission.
        
        Args:
            issue_number: The related issue number.
            title: The PR title.
            body: The PR description.
            file_changes: List of file change dictionaries.
            
        Returns:
            A dictionary containing the complete PR creation result.
        """
        branch_name = f"feature/issue-{issue_number}"
        
        # Step 1: Create branch (properly awaited)
        branch_result = await self.create_branch(branch_name)
        
        # Step 2: Convert and commit changes (properly awaited)
        changes = [
            FileChange(
                path=fc["path"],
                operation=fc["operation"],
                content=fc.get("content", "")
            )
            for fc in file_changes
        ]
        
        commit_message = f"feat: Implement issue #{issue_number}"
        commit_result = await self.commit_changes(branch_name, changes, commit_message)
        
        # Step 3: Create PR (properly awaited)
        pr_data = PRData(
            title=title,
            body=f"{body}\n\nCloses #{issue_number}",
            head=branch_name,
            base="main",
            issue_number=issue_number
        )
        pr_result = await self.create_pull_request(pr_data)
        
        return {
            "branch": branch_result,
            "commit": commit_result,
            "pull_request": pr_result,
            "status": "success",
        }
    
    def create_pr_sync(
        self,
        issue_number: int,
        title: str,
        body: str,
        file_changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synchronous wrapper for PR creation.
        
        This method provides a synchronous interface for PR creation,
        properly handling the async event loop.
        
        Args:
            issue_number: The related issue number.
            title: The PR title.
            body: The PR description.
            file_changes: List of file change dictionaries.
            
        Returns:
            A dictionary containing the complete PR creation result.
        """
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.create_pr_from_changes(
                    issue_number=issue_number,
                    title=title,
                    body=body,
                    file_changes=file_changes
                )
            )
        finally:
            loop.close()
