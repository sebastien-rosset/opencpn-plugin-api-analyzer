#!/usr/bin/env python3
"""Command-line interface for the OpenCPN Plugin API Analyzer."""

import argparse
import logging
import sys
from pathlib import Path
from collections import defaultdict

from opencpn_plugin_api_analyzer.analyzer import PluginAnalyzer
from opencpn_plugin_api_analyzer.report_generator import ReportGenerator
from opencpn_plugin_api_analyzer.xml_parser import XMLParser


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def get_api_header_url(api_version: str) -> str:
    """Get the URL for the API header file for a specific API version.

    Args:
        api_version: API version string (e.g., "1.18")

    Returns:
        URL to the API header file
    """
    # Extract the minor version number (e.g., "1.18" -> "18")
    version_parts = api_version.split(".")
    if len(version_parts) >= 2:
        version_num = version_parts[1]  # Take just the minor version number
    else:
        # Fallback if there is no dot in the version
        version_num = api_version

    # Use the OpenCPN libs repository which has version-specific API headers
    return f"https://raw.githubusercontent.com/OpenCPN/opencpn-libs/refs/heads/main/api-{version_num}/ocpn_plugin.h"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Analyze OpenCPN plugin API usage")

    parser.add_argument(
        "--ocpn-xml",
        type=str,
        default="https://github.com/OpenCPN/plugins/raw/master/ocpn-plugins.xml",
        help="URL or path to the OpenCPN plugins XML file",
    )

    parser.add_argument(
        "--single-target",
        action="store_true",
        help="For each plugin, analyze just one target to avoid duplicates",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./reports"),
        help="Directory to store analysis reports",
    )

    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("./workdir"),
        help="Working directory for temporary files",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean the working directory before analysis",
    )

    parser.add_argument(
        "--plugins",
        type=str,
        nargs="*",
        help="Specific plugins to analyze (default: analyze all)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "html", "markdown"],
        default="markdown",
        help="Output format for the report",
    )

    return parser.parse_args()


def main() -> int:
    """Run the OpenCPN Plugin API Analyzer.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    setup_logging(args.verbose)

    logging.info("Starting OpenCPN Plugin API Analyzer")

    try:
        # Create output directory if it doesn't exist
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Create work directory if it doesn't exist
        args.work_dir.mkdir(parents=True, exist_ok=True)

        # Parse the plugins XML file to get API versions
        xml_parser = XMLParser(args.ocpn_xml)
        plugins = xml_parser.parse()

        # Group plugins by API version and filter if specific plugins were requested
        plugins_by_api_version = {}
        analyzed_plugins = set()

        for name, plugin in plugins.items():
            if args.plugins and name not in args.plugins:
                continue

            if not plugin.api_version or not plugin.source_repo:
                continue

            # If analyzing a single target per version and this plugin has already been analyzed
            # with this API version, skip it
            if args.single_target:
                plugin_key = (name, plugin.api_version)
                if plugin_key in analyzed_plugins:
                    continue
                analyzed_plugins.add(plugin_key)

            if plugin.api_version not in plugins_by_api_version:
                plugins_by_api_version[plugin.api_version] = {}

            plugins_by_api_version[plugin.api_version][name] = plugin

        # If there are no plugins to analyze, exit early
        if not plugins_by_api_version:
            logging.warning("No plugins found to analyze.")
            return 0

        # Overall results
        all_results = {}

        # Analyze plugins for each API version
        for api_version, version_plugins in plugins_by_api_version.items():
            logging.info(f"Analyzing plugins for API version {api_version}...")

            # Get the URL for the API header file for this version
            api_header_url = get_api_header_url(api_version)
            logging.info(f"Using API header: {api_header_url}")

            # Initialize analyzer for this API version
            analyzer = PluginAnalyzer(
                api_header_url=api_header_url,
                plugins_xml_url=args.ocpn_xml,
                work_dir=args.work_dir,
                clean=args.clean,
            )

            # Get plugin names for this version
            plugin_names = list(version_plugins.keys())
            logging.info(
                f"Analyzing {len(plugin_names)} plugins for API version {api_version}"
            )

            # Run analysis for this version
            results = analyzer.analyze_plugins(plugin_names=plugin_names)

            # Add results to overall results
            all_results.update(results)

        # Generate report
        report_generator = ReportGenerator(
            output_dir=args.output_dir,
            format=args.format,
        )
        report_generator.generate(all_results)

        logging.info(f"Analysis complete. Reports saved to {args.output_dir}")
        return 0

    except Exception as e:
        logging.exception(f"Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
