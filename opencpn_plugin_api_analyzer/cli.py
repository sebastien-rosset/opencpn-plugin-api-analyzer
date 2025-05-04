#!/usr/bin/env python3
"""Command-line interface for the OpenCPN Plugin API Analyzer."""

import argparse
import logging
import sys
from pathlib import Path

from opencpn_plugin_api_analyzer.analyzer import PluginAnalyzer
from opencpn_plugin_api_analyzer.report_generator import ReportGenerator


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
        "--api-header",
        type=str,
        default="https://raw.githubusercontent.com/OpenCPN/OpenCPN/master/include/ocpn_plugin.h",
        help="URL or path to the OpenCPN plugin API header file",
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
        "--verbose", "-v",
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
        
        # Initialize analyzer and perform analysis
        analyzer = PluginAnalyzer(
            api_header_url=args.api_header,
            plugins_xml_url=args.ocpn_xml,
            work_dir=args.work_dir,
            clean=args.clean,
        )
        
        # Run analysis on all plugins or specified plugins
        results = analyzer.analyze_plugins(plugin_names=args.plugins)
        
        # Generate report
        report_generator = ReportGenerator(
            output_dir=args.output_dir,
            format=args.format,
        )
        report_generator.generate(results)
        
        logging.info(f"Analysis complete. Reports saved to {args.output_dir}")
        return 0
    
    except Exception as e:
        logging.exception(f"Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())