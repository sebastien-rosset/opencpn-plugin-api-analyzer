"""Handler for Git repositories."""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

import git
from tqdm import tqdm


class RepoHandler:
    """Handler for Git repositories."""
    
    def __init__(self, work_dir: Path, clean: bool = False):
        """Initialize the repository handler.
        
        Args:
            work_dir: Working directory for cloning repositories.
            clean: Whether to clean the working directory before cloning.
        """
        self.work_dir = work_dir
        self.logger = logging.getLogger(__name__)
        
        # Create work directory if it doesn't exist
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean work directory if requested
        if clean and self.work_dir.exists():
            self.logger.info(f"Cleaning work directory: {self.work_dir}")
            shutil.rmtree(self.work_dir)
            self.work_dir.mkdir(parents=True)
    
    def _sanitize_repo_name(self, repo_url: str) -> str:
        """Sanitize repository URL to use as directory name.
        
        Args:
            repo_url: Repository URL.
            
        Returns:
            Sanitized directory name.
        """
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1]
        
        # Remove .git suffix if present
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        # Ensure the name is valid for a directory
        repo_name = re.sub(r'[^\w.-]', '_', repo_name)
        
        return repo_name
    
    def clone_repo(self, repo_url: str) -> Optional[Path]:
        """Clone a repository.
        
        Args:
            repo_url: Repository URL.
            
        Returns:
            Path to the cloned repository, or None if cloning failed.
        """
        if not repo_url:
            self.logger.warning("No repository URL provided")
            return None
        
        repo_name = self._sanitize_repo_name(repo_url)
        repo_dir = self.work_dir / repo_name
        
        # Check if the repository already exists
        if repo_dir.exists():
            self.logger.info(f"Repository already exists: {repo_dir}")
            try:
                # Try to update the repository
                repo = git.Repo(repo_dir)
                self.logger.info(f"Updating repository: {repo_url}")
                repo.git.fetch('--all')
                repo.git.reset('--hard', 'origin/master')
                self.logger.info(f"Repository updated: {repo_dir}")
                return repo_dir
            except git.GitCommandError as e:
                self.logger.warning(f"Failed to update repository: {e}")
                # Continue with a fresh clone
                shutil.rmtree(repo_dir)
        
        # Clone the repository
        try:
            self.logger.info(f"Cloning repository: {repo_url}")
            git.Repo.clone_from(repo_url, repo_dir, depth=1)
            self.logger.info(f"Repository cloned: {repo_dir}")
            return repo_dir
        except git.GitCommandError as e:
            self.logger.error(f"Failed to clone repository: {e}")
            return None
    
    def find_cpp_files(self, repo_dir: Path) -> List[Path]:
        """Find C++ source files in a repository.
        
        Args:
            repo_dir: Path to the repository.
            
        Returns:
            List of paths to C++ source files.
        """
        if not repo_dir.exists():
            return []
        
        cpp_files = []
        
        # Exclude common directories that aren't likely to contain plugin code
        excludes = [
            'build', 'cmake', 'CMake', 'libs', 'lib', 'extern',
            'external', '3rdparty', 'third_party', 'tests', 'test',
            'doc', 'docs', 'data', 'resources', 'res', '.git'
        ]
        
        for root, dirs, files in os.walk(repo_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in excludes]
            
            root_path = Path(root)
            
            # Find C++ source files
            for file in files:
                if file.endswith(('.cpp', '.cxx', '.cc', '.c', '.hpp', '.hxx', '.hh', '.h')):
                    cpp_files.append(root_path / file)
        
        return cpp_files