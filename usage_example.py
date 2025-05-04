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

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration
API_HEADER_URL = (
    "https://raw.githubusercontent.com/OpenCPN/OpenCPN/master/include/ocpn_plugin.h"
)
PLUGINS_XML_URL = "https://github.com/OpenCPN/plugins/raw/master/ocpn-plugins.xml"
WORK_DIR = Path("./workdir")
OUTPUT_DIR = Path("./reports")
REPORT_FORMAT = "markdown"  # Options: markdown, html, csv, json

# Optional: Specific plugins to analyze (leave empty to analyze all)
PLUGINS_TO_ANALYZE = [
    "AutoTrackRaymarine",
    # Add more plugin names here
]


def main():
    """Run the API analyzer example."""
    print("Starting OpenCPN Plugin API Analyzer...")

    # Initialize analyzer
    analyzer = PluginAnalyzer(
        api_header_url=API_HEADER_URL,
        plugins_xml_url=PLUGINS_XML_URL,
        work_dir=WORK_DIR,
        clean=False,  # Set to True to clean work directory before analysis
    )

    # Run analysis
    print(f"Analyzing {'specific plugins' if PLUGINS_TO_ANALYZE else 'all plugins'}...")
    results = analyzer.analyze_plugins(
        plugin_names=PLUGINS_TO_ANALYZE if PLUGINS_TO_ANALYZE else None
    )

    # Generate report
    print(f"Generating {REPORT_FORMAT} report...")
    report_generator = ReportGenerator(output_dir=OUTPUT_DIR, format=REPORT_FORMAT)
    report_generator.generate(results)

    print(f"Analysis complete! Reports saved to {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
