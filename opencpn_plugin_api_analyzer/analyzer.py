"""Main analyzer module for the OpenCPN Plugin API Analyzer."""

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import clang.cindex
from tqdm import tqdm

from opencpn_plugin_api_analyzer.api_parser import ApiHeaderParser, ApiSymbol
from opencpn_plugin_api_analyzer.repo_handler import RepoHandler
from opencpn_plugin_api_analyzer.xml_parser import Plugin, XMLParser


class PluginAnalyzer:
    """Main analyzer for OpenCPN plugin API usage."""

    def __init__(
        self,
        api_header_url: str,
        plugins_xml_url: str,
        work_dir: Path,
        clean: bool = False,
    ):
        """Initialize the plugin analyzer.

        Args:
            api_header_url: URL or path to the OpenCPN plugin API header file.
            plugins_xml_url: URL or path to the OpenCPN plugins XML file.
            work_dir: Working directory for temporary files.
            clean: Whether to clean the working directory before analysis.
        """
        self.api_header_url = api_header_url
        self.plugins_xml_url = plugins_xml_url
        self.work_dir = work_dir
        self.clean = clean
        self.logger = logging.getLogger(__name__)

        # Create work directory if it doesn't exist
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.api_parser = ApiHeaderParser(api_header_url)
        self.xml_parser = XMLParser(plugins_xml_url)
        self.repo_handler = RepoHandler(work_dir / "repos", clean)

        # Cache for parsed data
        self.api_symbols = None
        self.plugins = None

    def _get_api_symbols(self) -> Dict[str, ApiSymbol]:
        """Get API symbols from the header file.

        Returns:
            Dictionary mapping symbol names to ApiSymbol objects.
        """
        if self.api_symbols is None:
            self.api_symbols = self.api_parser.parse()
        return self.api_symbols

    def _get_plugins(self) -> Dict[str, Plugin]:
        """Get plugins from the XML file.

        Returns:
            Dictionary mapping plugin names to Plugin objects.
        """
        if self.plugins is None:
            self.plugins = self.xml_parser.parse()
        return self.plugins

    def _analyze_file_content(
        self, file_path: Path, api_symbols: Dict[str, ApiSymbol]
    ) -> Set[str]:
        """Analyze a file for API symbol usage.

        This function uses more sophisticated analysis than simple string matching
        to reduce false positives and false negatives.

        Args:
            file_path: Path to the file to analyze.
            api_symbols: Dictionary of API symbols to look for.

        Returns:
            Set of API symbol names found in the file.
        """
        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            self.logger.warning(f"Failed to read file {file_path}: {e}")
            return set()

        found_symbols = set()

        # Check for direct includes of the plugin API header
        if "ocpn_plugin.h" in content:
            self.logger.debug(f"Found direct include of ocpn_plugin.h in {file_path}")

        # First pass: Identify potential matches using regex to avoid parsing non-matches
        # Create a regex pattern with all API symbol names
        symbol_names = list(api_symbols.keys())

        # Sort by length (descending) to avoid partial matches
        symbol_names.sort(key=len, reverse=True)

        # Split the list into chunks to avoid regex overflow
        chunk_size = 100
        symbols_to_check = set()

        for i in range(0, len(symbol_names), chunk_size):
            chunk = symbol_names[i : i + chunk_size]

            # Create a regex pattern that matches whole words
            # to reduce false positives from substring matches
            pattern = (
                r"\b(?:"
                + "|".join(re.escape(s.split("::")[-1]) for s in chunk)
                + r")\b"
            )
            matches = re.findall(pattern, content)

            if matches:
                # For each match, find the corresponding full symbol names
                for match in matches:
                    for symbol in chunk:
                        if symbol.split("::")[-1] == match:
                            symbols_to_check.add(symbol)

        if not symbols_to_check:
            return found_symbols

        # Second pass: More careful analysis of potential matches
        for symbol_name in symbols_to_check:
            symbol = api_symbols[symbol_name]
            short_name = symbol_name.split("::")[-1]

            # Look for exact matches outside of comments and strings
            # Split the content into lines and analyze each line to avoid look-behind issues
            pattern = re.compile(r"\b" + re.escape(short_name) + r"\b")

            # Check if pattern exists outside of comments and strings
            match_found = False
            for line in content.splitlines():
                # Skip comment lines
                if line.strip().startswith("//"):
                    continue

                # For each line, check if it contains the pattern outside of quotes
                line_parts = []
                in_quote = False
                start_idx = 0

                for i, char in enumerate(line):
                    if char == '"' and (
                        i == 0 or line[i - 1] != "\\"
                    ):  # Handle escaped quotes
                        if in_quote:
                            # End of quoted section
                            in_quote = False
                            start_idx = i + 1
                        else:
                            # Start of quoted section - add non-quoted part to line_parts
                            if i > start_idx:
                                line_parts.append(line[start_idx:i])
                            in_quote = True
                            start_idx = i + 1

                # Add the last part if it's not in quotes
                if not in_quote and start_idx < len(line):
                    line_parts.append(line[start_idx:])

                # Check for pattern in non-quoted parts
                for part in line_parts:
                    if pattern.search(part):
                        match_found = True
                        break

                if match_found:
                    break

            if match_found:
                # Additional checks to reduce false positives

                # For methods, check if they're called as member functions
                if (
                    symbol.kind in ("CXX_METHOD", "FUNCTION_DECL")
                    and "::" in symbol_name
                ):
                    class_name = symbol_name.split("::")[-2]
                    # Look for pattern like "obj.method(" or "Class::method("
                    method_pattern = (
                        r"\b"
                        + re.escape(class_name)
                        + r"(?:::|\.)"
                        + re.escape(short_name)
                        + r"\s*\("
                    )
                    if re.search(method_pattern, content):
                        found_symbols.add(symbol_name)
                        continue

                # For classes, check if they're used in declarations
                if symbol.kind in ("CLASS_DECL", "STRUCT_DECL"):
                    # Look for pattern like "Class var" or "Class* var" or "Class &var"
                    class_pattern = (
                        r"\b" + re.escape(short_name) + r"\s*(?:\*|\&)?\s*\w+"
                    )
                    if re.search(class_pattern, content):
                        found_symbols.add(symbol_name)
                        continue

                # For enum constants, check if they're used with the enum prefix
                if symbol.kind == "ENUM_CONSTANT_DECL" and "::" in symbol_name:
                    enum_name = symbol_name.split("::")[-2]
                    # Look for pattern like "Enum::CONSTANT" or "using Enum; ... CONSTANT"
                    enum_pattern = (
                        r"\b"
                        + re.escape(enum_name)
                        + r"::"
                        + re.escape(short_name)
                        + r"\b"
                    )
                    using_pattern = (
                        r"using\s+(?:namespace\s+)?"
                        + re.escape(enum_name)
                        + r"\s*;.*\b"
                        + re.escape(short_name)
                        + r"\b"
                    )
                    if re.search(enum_pattern, content) or re.search(
                        using_pattern, content, re.DOTALL
                    ):
                        found_symbols.add(symbol_name)
                        continue

                # For macros and simple functions, just finding the name is usually enough
                if (
                    symbol.kind in ("MACRO_DEFINITION", "FUNCTION_DECL")
                    and "::" not in symbol_name
                ):
                    found_symbols.add(symbol_name)
                    continue

                # Fallback: if we made it here but the name is rare/unique enough, include it
                # Count occurrences to help judge uniqueness
                occurrences = len(
                    re.findall(r"\b" + re.escape(short_name) + r"\b", content)
                )
                if occurrences > 0 and occurrences < 5 and len(short_name) > 5:
                    # If the name is long enough and not too common, it's likely a match
                    found_symbols.add(symbol_name)

        return found_symbols

    def _analyze_plugin_repo(
        self, plugin_name: str, repo_path: Path, api_symbols: Dict[str, ApiSymbol]
    ) -> Dict[str, int]:
        """Analyze a plugin repository for API usage.

        Args:
            plugin_name: Name of the plugin.
            repo_path: Path to the repository.
            api_symbols: Dictionary of API symbols to look for.

        Returns:
            Dictionary mapping API symbol names to occurrence counts.
        """
        self.logger.info(f"Analyzing repository for plugin: {plugin_name}")

        # Find C++ source files
        cpp_files = self.repo_handler.find_cpp_files(repo_path)
        self.logger.info(f"Found {len(cpp_files)} C++ files in {plugin_name}")

        # Track symbol occurrences
        symbol_counts = defaultdict(int)

        # Analyze each file
        for file_path in tqdm(cpp_files, desc=f"Analyzing {plugin_name}", leave=False):
            symbols_found = self._analyze_file_content(file_path, api_symbols)
            for symbol in symbols_found:
                symbol_counts[symbol] += 1

        return dict(symbol_counts)

    def analyze_plugins(
        self, plugin_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Analyze plugins for API usage.

        Args:
            plugin_names: List of plugin names to analyze. If None, analyze all plugins.

        Returns:
            Dictionary mapping API versions to maps of plugin names to API symbol counts.
            Example:
            {
                "api_version_1.16": {
                    "Plugin1": {"API_Symbol1": 5, "API_Symbol2": 3},
                    "Plugin2": {"API_Symbol1": 2}
                }
            }
        """
        # Get API symbols and plugins
        api_symbols = self._get_api_symbols()
        plugins = self._get_plugins()

        self.logger.info(
            f"Found {len(api_symbols)} API symbols and {len(plugins)} plugins"
        )

        # Filter plugins if requested
        if plugin_names:
            plugins = {
                name: plugin for name, plugin in plugins.items() if name in plugin_names
            }
            self.logger.info(f"Filtered to {len(plugins)} requested plugins")

        # Group plugins by API version
        plugins_by_api = defaultdict(dict)
        for name, plugin in plugins.items():
            # Skip plugins without source repo
            if not plugin.source_repo or not plugin.api_version:
                self.logger.warning(
                    f"Skipping plugin without source or API version: {name}"
                )
                continue

            # Normalize API version
            api_version = f"api_version_{plugin.api_version}"
            plugins_by_api[api_version][name] = plugin

        # Analyze plugins
        results = defaultdict(dict)

        for api_version, api_plugins in plugins_by_api.items():
            self.logger.info(f"Analyzing plugins for API version: {api_version}")

            for name, plugin in tqdm(
                api_plugins.items(), desc=f"Processing {api_version}"
            ):
                # Clone repository with specific version checkout
                repo_path = self.repo_handler.clone_repo(
                    plugin.source_repo,
                    version=plugin.version  # Use the plugin version for checkout
                )

                if not repo_path:
                    self.logger.warning(
                        f"Failed to clone repository for plugin: {name}"
                    )
                    continue

                # Analyze repository
                symbol_counts = self._analyze_plugin_repo(name, repo_path, api_symbols)

                # Store results
                if symbol_counts:
                    results[api_version][name] = symbol_counts
                    self.logger.info(
                        f"Plugin {name} (v{plugin.version}) uses {len(symbol_counts)} API symbols"
                    )

        return dict(results)
