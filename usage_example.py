#!/usr/bin/env python3
"""
Example script for using the OpenCPN Plugin API Analyzer.

This script demonstrates how to use the analyzer programmatically
rather than through the CLI interface.
"""

import logging
from pathlib import Path

from opencpn_plugin_api_analyzer.analyzer import PluginAnalyzer
from opencpn_plugin_api_analyzer.report_generator import ReportGenerator
from opencpn_plugin_api_analyzer.xml_parser import XMLParser

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration
PLUGINS_XML_URL = "https://github.com/OpenCPN/plugins/raw/master/ocpn-plugins.xml"
WORK_DIR = Path("./workdir")
OUTPUT_DIR = Path("./reports")
REPORT_FORMAT = "markdown"  # Options: markdown, html, csv, json

# API header URL template for specific versions
API_URL_TEMPLATE = "https://raw.githubusercontent.com/OpenCPN/opencpn-libs/refs/heads/main/api-{version}/ocpn_plugin.h"

# Optional: Specific plugins to analyze (leave empty to analyze all)
PLUGINS_TO_ANALYZE = [
    "AutoTrackRaymarine",
    "Calculator",
    "CanadianTides",
    "Climatology",
    "DR",
    "DashboardSK",
    "EarthExplorer",
    "IACFleet",
    "Polar",
    "VDR",
    "Watchdog",
    # "WeatherRouting",
    # Add more plugin names here
]

# For each target, analyze just the first one found (to avoid duplicates)
ANALYZE_SINGLE_TARGET = True


def get_api_header_url(api_version):
    """Get the URL for the API header file for a specific API version."""
    # Extract the minor version number (e.g., "1.18" -> "18")
    # Split the version at the dot and take the second part
    version_parts = api_version.split(".")
    if len(version_parts) >= 2:
        version_num = version_parts[1]  # Take just the minor version number
    else:
        # Fallback if there is no dot in the version
        version_num = api_version

    return API_URL_TEMPLATE.format(version=version_num)


def main():
    """Run the API analyzer example."""
    print("Starting OpenCPN Plugin API Analyzer...")

    # Parse the plugins XML file to get API versions
    xml_parser = XMLParser(PLUGINS_XML_URL)
    plugins = xml_parser.parse()

    # Group plugins by API version and filter if specific plugins were requested
    plugins_by_api_version = {}
    analyzed_plugins = set()

    for name, plugin in plugins.items():
        if PLUGINS_TO_ANALYZE and name not in PLUGINS_TO_ANALYZE:
            continue

        if not plugin.api_version or not plugin.source_repo:
            continue

        # If we're analyzing a single target per version and this plugin has already been analyzed
        # with this API version, skip it
        plugin_key = (name, plugin.api_version)
        if ANALYZE_SINGLE_TARGET and plugin_key in analyzed_plugins:
            continue

        if plugin.api_version not in plugins_by_api_version:
            plugins_by_api_version[plugin.api_version] = {}

        plugins_by_api_version[plugin.api_version][name] = plugin
        analyzed_plugins.add(plugin_key)

    # Overall results
    all_results = {}

    # Analyze plugins for each API version
    for api_version, version_plugins in plugins_by_api_version.items():
        print(f"Analyzing plugins for API version {api_version}...")

        # Get the URL for the API header file for this version
        api_header_url = get_api_header_url(api_version)
        print(f"Using API header: {api_header_url}")

        # Initialize analyzer for this API version
        analyzer = PluginAnalyzer(
            api_header_url=api_header_url,
            plugins_xml_url=PLUGINS_XML_URL,
            work_dir=WORK_DIR,
            clean=False,  # Set to True to clean work directory before analysis
        )

        # Get plugin names for this version
        plugin_names = list(version_plugins.keys())
        print(
            f"Analyzing {len(plugin_names)} plugins for API version {api_version}: {', '.join(plugin_names)}"
        )

        # Run analysis for this version
        results = analyzer.analyze_plugins(plugin_names=plugin_names)

        # Add results to overall results
        all_results.update(results)

    # Generate report
    print(f"Generating {REPORT_FORMAT} report...")
    report_generator = ReportGenerator(output_dir=OUTPUT_DIR, format=REPORT_FORMAT)
    report_generator.generate(all_results)

    print(f"Analysis complete! Reports saved to {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
