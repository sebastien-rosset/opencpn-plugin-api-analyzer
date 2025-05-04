"""Generate reports from the analysis results."""

from collections import defaultdict
import csv
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Optional


class ReportGenerator:
    """Generate reports from the analysis results."""

    def __init__(self, output_dir: Path, format: str = "markdown") -> None:
        """Initialize the report generator.

        Args:
            output_dir: Directory to store the reports
            format: Output format (csv, json, html, markdown)
        """
        self.output_dir = output_dir
        self.format = format
        self.logger = logging.getLogger(__name__)

    def _generate_markdown_report(self, results: Dict[str, Any]) -> None:
        """Generate a Markdown report.

        Args:
            results: Analysis results organized by API version then plugin name
        """
        report_path = self.output_dir / "report.md"

        # Extract all API versions from the results
        api_versions = list(results.keys())

        with open(report_path, "w") as f:
            f.write("# OpenCPN Plugin API Usage Report\n\n")

            # Generate plugin summary with API versions
            f.write("## Plugin Summary\n\n")
            f.write("| Plugin Name | API Version |\n")
            f.write("|------------|-------------|\n")

            # Create a flattened plugin list for sorting
            all_plugins = []
            for api_version, plugins in results.items():
                for plugin_name, symbols in plugins.items():
                    # Extract version number from api_version_X.XX format
                    version_number = api_version.replace("api_version_", "")
                    all_plugins.append((plugin_name, version_number))

            # Sort plugins alphabetically
            for plugin_name, version_number in sorted(
                all_plugins, key=lambda x: x[0].lower()
            ):
                f.write(f"| {plugin_name} | {version_number} |\n")

            f.write("\n## API Symbol Usage\n\n")

            # Count symbol usage across all plugins
            all_symbols = defaultdict(list)
            for api_version, plugins in results.items():
                for plugin_name, symbols in plugins.items():
                    for symbol in symbols:
                        all_symbols[symbol].append(plugin_name)

            # Sort symbols by usage count (descending)
            sorted_symbols = sorted(
                all_symbols.items(), key=lambda item: len(item[1]), reverse=True
            )

            # Write the overall symbol usage
            f.write("| Symbol | Plugins Using | Plugin Names |\n")
            f.write("|--------|--------------|-------------|\n")
            for symbol, plugins in sorted_symbols:
                plugin_names = ", ".join(plugins)
                f.write(f"| `{symbol}` | {len(plugins)} | {plugin_names} |\n")

            # Report by API version
            for api_version in sorted(api_versions):
                version_number = api_version.replace("api_version_", "")
                f.write(f"\n\n### API Version {version_number}\n\n")
                f.write("| Symbol | Plugins Using | Plugin Names |\n")
                f.write("|--------|--------------|-------------|\n")

                # Collect symbols for this API version
                version_symbols = defaultdict(list)
                for plugin_name, symbols in results[api_version].items():
                    for symbol in symbols:
                        version_symbols[symbol].append(plugin_name)

                # Sort symbols by usage count (descending)
                sorted_version_symbols = sorted(
                    version_symbols.items(), key=lambda item: len(item[1]), reverse=True
                )

                for symbol, plugins in sorted_version_symbols:
                    plugin_names = ", ".join(plugins)
                    f.write(f"| `{symbol}` | {len(plugins)} | {plugin_names} |\n")

    def _generate_csv_report(self, results: Dict[str, Any]) -> None:
        """Generate a CSV report.

        Args:
            results: Analysis results organized by API version then plugin name
        """
        report_path = self.output_dir / "report.csv"

        # Collect all symbols across all plugins
        all_symbols = set()
        for api_version, plugins in results.items():
            for plugin_name, symbols in plugins.items():
                all_symbols.update(symbols)

        # Create a flattened plugin list
        plugin_data = []
        for api_version, plugins in results.items():
            version_number = api_version.replace("api_version_", "")
            for plugin_name, symbols in plugins.items():
                plugin_data.append((plugin_name, version_number, symbols))

        with open(report_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            header = ["Plugin", "API Version"] + list(sorted(all_symbols))
            writer.writerow(header)

            # Sort plugins alphabetically
            plugin_data.sort(key=lambda x: x[0].lower())

            # Write data
            for plugin_name, version_number, symbols in plugin_data:
                row = [plugin_name, version_number]
                for symbol in sorted(all_symbols):
                    if symbol in symbols:
                        row.append("X")
                    else:
                        row.append("")
                writer.writerow(row)

    def _generate_json_report(self, results: Dict[str, Any]) -> None:
        """Generate a JSON report.

        Args:
            results: Analysis results organized by API version then plugin name
        """
        report_path = self.output_dir / "report.json"

        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)

    def _generate_html_report(self, results: Dict[str, Any]) -> None:
        """Generate an HTML report.

        Args:
            results: Analysis results organized by API version then plugin name
        """
        report_path = self.output_dir / "report.html"

        # Extract all API versions from the results
        api_versions = list(results.keys())

        with open(report_path, "w") as f:
            f.write(
                """<!DOCTYPE html>
<html>
<head>
    <title>OpenCPN Plugin API Usage Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; }
        th { background-color: #f2f2f2; text-align: left; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        h1, h2, h3 { color: #005580; }
        .code { font-family: monospace; }
    </style>
</head>
<body>
    <h1>OpenCPN Plugin API Usage Report</h1>
    
    <h2>Plugin Summary</h2>
    <table>
        <tr>
            <th>Plugin Name</th>
            <th>API Version</th>
        </tr>
"""
            )

            # Create a flattened plugin list for sorting
            all_plugins = []
            for api_version, plugins in results.items():
                version_number = api_version.replace("api_version_", "")
                for plugin_name in plugins.keys():
                    all_plugins.append((plugin_name, version_number))

            # Sort plugins alphabetically
            for plugin_name, version_number in sorted(
                all_plugins, key=lambda x: x[0].lower()
            ):
                f.write(
                    f"        <tr><td>{plugin_name}</td><td>{version_number}</td></tr>\n"
                )

            f.write(
                """    </table>
            
    <h2>API Symbol Usage</h2>
    <table>
        <tr>
            <th>Symbol</th>
            <th>Plugins Using</th>
            <th>Plugin Names</th>
        </tr>
"""
            )

            # Count symbol usage across all plugins
            all_symbols = defaultdict(list)
            for api_version, plugins in results.items():
                for plugin_name, symbols in plugins.items():
                    for symbol in symbols:
                        all_symbols[symbol].append(plugin_name)

            # Sort symbols by usage count (descending)
            sorted_symbols = sorted(
                all_symbols.items(), key=lambda item: len(item[1]), reverse=True
            )

            for symbol, plugins in sorted_symbols:
                plugin_names = ", ".join(plugins)
                f.write(
                    f'        <tr><td class="code">{symbol}</td><td>{len(plugins)}</td><td>{plugin_names}</td></tr>\n'
                )

            f.write("    </table>\n")

            # Report by API version
            for api_version in sorted(api_versions):
                version_number = api_version.replace("api_version_", "")
                f.write(
                    f"""
    <h3>API Version {version_number}</h3>
    <table>
        <tr>
            <th>Symbol</th>
            <th>Plugins Using</th>
            <th>Plugin Names</th>
        </tr>
"""
                )

                # Collect symbols for this API version
                version_symbols = defaultdict(list)
                for plugin_name, symbols in results[api_version].items():
                    for symbol in symbols:
                        version_symbols[symbol].append(plugin_name)

                # Sort symbols by usage count (descending)
                sorted_version_symbols = sorted(
                    version_symbols.items(), key=lambda item: len(item[1]), reverse=True
                )

                for symbol, plugins in sorted_version_symbols:
                    plugin_names = ", ".join(plugins)
                    f.write(
                        f'        <tr><td class="code">{symbol}</td><td>{len(plugins)}</td><td>{plugin_names}</td></tr>\n'
                    )

                f.write("    </table>\n")

            f.write(
                """</body>
</html>"""
            )

    def generate(self, results: Dict[str, Any]) -> None:
        """Generate reports from the analysis results.

        Args:
            results: Analysis results organized by API version then plugin name
        """
        self.logger.info(f"Generating {self.format} report")

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        if self.format == "markdown":
            self._generate_markdown_report(results)
        elif self.format == "csv":
            self._generate_csv_report(results)
        elif self.format == "json":
            self._generate_json_report(results)
        elif self.format == "html":
            self._generate_html_report(results)
        else:
            self.logger.warning(f"Unsupported format: {self.format}, using markdown")
            self._generate_markdown_report(results)

        self.logger.info(f"Report saved to {self.output_dir}")
