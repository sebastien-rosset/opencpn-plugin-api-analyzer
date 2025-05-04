"""Generate reports from analysis results."""

import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd


class ReportGenerator:
    """Generate reports from analysis results."""
    
    def __init__(self, output_dir: Path, format: str = "markdown"):
        """Initialize the report generator.
        
        Args:
            output_dir: Directory to store generated reports.
            format: Output format (csv, json, html, markdown).
        """
        self.output_dir = output_dir
        self.format = format
        self.logger = logging.getLogger(__name__)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_api_to_plugin_map(
        self, results: Dict[str, Dict[str, Dict[str, int]]]
    ) -> Dict[str, Dict[str, Set[str]]]:
        """Generate a mapping from API symbols to plugins that use them.
        
        Args:
            results: Analysis results.
            
        Returns:
            Dictionary mapping API versions to maps of API symbols to sets of plugins.
        """
        api_to_plugins = defaultdict(lambda: defaultdict(set))
        
        for api_version, plugins in results.items():
            for plugin_name, symbols in plugins.items():
                for symbol_name in symbols:
                    api_to_plugins[api_version][symbol_name].add(plugin_name)
        
        return {
            api_version: dict(symbols)
            for api_version, symbols in api_to_plugins.items()
        }
    
    def _generate_markdown(
        self,
        results: Dict[str, Dict[str, Dict[str, int]]],
        api_to_plugins: Dict[str, Dict[str, Set[str]]],
    ) -> str:
        """Generate a Markdown report.
        
        Args:
            results: Analysis results.
            api_to_plugins: Mapping from API symbols to plugins.
            
        Returns:
            Markdown report as a string.
        """
        report = ["# OpenCPN Plugin API Usage Report\n"]
        
        # Summary
        total_plugins = sum(len(plugins) for plugins in results.values())
        total_api_symbols = sum(
            len(set().union(*(symbols.keys() for symbols in plugins.values())))
            for plugins in results.values()
        )
        
        report.append(f"## Summary\n")
        report.append(f"- Total plugins analyzed: {total_plugins}")
        report.append(f"- Total API symbols used: {total_api_symbols}")
        report.append(f"- API versions: {', '.join(sorted(results.keys()))}\n")
        
        # API usage by plugin
        report.append(f"## API Usage by Plugin\n")
        for api_version, plugins in sorted(results.items()):
            report.append(f"### {api_version}\n")
            for plugin_name, symbols in sorted(plugins.items()):
                report.append(f"#### {plugin_name}\n")
                report.append(f"- Uses {len(symbols)} API symbols")
                
                # List symbols by type
                symbols_by_type = defaultdict(list)
                for symbol_name, count in sorted(symbols.items()):
                    # Simple symbol type extraction (assuming symbols follow a pattern)
                    if '::' in symbol_name:
                        parts = symbol_name.split('::')
                        if len(parts) >= 2:
                            symbol_type = parts[-2]
                        else:
                            symbol_type = "Other"
                    else:
                        symbol_type = "Global"
                    
                    symbols_by_type[symbol_type].append((symbol_name, count))
                
                for symbol_type, type_symbols in sorted(symbols_by_type.items()):
                    report.append(f"\n##### {symbol_type}")
                    report.append("| Symbol | Occurrences |")
                    report.append("|--------|-------------|")
                    for symbol_name, count in sorted(type_symbols):
                        report.append(f"| `{symbol_name}` | {count} |")
                
                report.append("\n")
        
        # API popularity ranking
        report.append(f"## API Symbol Popularity\n")
        for api_version, symbols in sorted(api_to_plugins.items()):
            report.append(f"### {api_version}\n")
            
            # Sort symbols by number of plugins using them
            sorted_symbols = sorted(
                symbols.items(),
                key=lambda x: (len(x[1]), x[0]),
                reverse=True
            )
            
            report.append("| Symbol | Plugins Using | Plugin Names |")
            report.append("|--------|--------------|-------------|")
            
            for symbol_name, plugin_set in sorted_symbols:
                plugin_count = len(plugin_set)
                plugin_list = ", ".join(sorted(plugin_set))
                report.append(f"| `{symbol_name}` | {plugin_count} | {plugin_list} |")
            
            report.append("\n")
        
        return "\n".join(report)
    
    def _generate_csv(
        self,
        results: Dict[str, Dict[str, Dict[str, int]]],
        api_to_plugins: Dict[str, Dict[str, Set[str]]],
    ) -> Dict[str, str]:
        """Generate CSV reports.
        
        Args:
            results: Analysis results.
            api_to_plugins: Mapping from API symbols to plugins.
            
        Returns:
            Dictionary mapping report file names to CSV content.
        """
        reports = {}
        
        # Plugin to API mapping
        for api_version, plugins in results.items():
            rows = []
            for plugin_name, symbols in plugins.items():
                for symbol_name, count in symbols.items():
                    rows.append({
                        "API_Version": api_version,
                        "Plugin": plugin_name,
                        "Symbol": symbol_name,
                        "Occurrences": count
                    })
            
            if rows:
                df = pd.DataFrame(rows)
                csv_content = df.to_csv(index=False)
                reports[f"plugin_to_api_{api_version}.csv"] = csv_content
        
        # API to plugin mapping
        for api_version, symbols in api_to_plugins.items():
            rows = []
            for symbol_name, plugin_set in symbols.items():
                rows.append({
                    "API_Version": api_version,
                    "Symbol": symbol_name,
                    "Plugin_Count": len(plugin_set),
                    "Plugins": ", ".join(sorted(plugin_set))
                })
            
            if rows:
                df = pd.DataFrame(rows)
                df = df.sort_values("Plugin_Count", ascending=False)
                csv_content = df.to_csv(index=False)
                reports[f"api_to_plugin_{api_version}.csv"] = csv_content
        
        return reports
    
    def _generate_json(
        self,
        results: Dict[str, Dict[str, Dict[str, int]]],
        api_to_plugins: Dict[str, Dict[str, Set[str]]],
    ) -> Dict[str, str]:
        """Generate JSON reports.
        
        Args:
            results: Analysis results.
            api_to_plugins: Mapping from API symbols to plugins.
            
        Returns:
            Dictionary mapping report file names to JSON content.
        """
        reports = {}
        
        # Convert set objects to lists for JSON serialization
        json_api_to_plugins = {}
        for api_version, symbols in api_to_plugins.items():
            json_api_to_plugins[api_version] = {
                symbol: list(plugins) for symbol, plugins in symbols.items()
            }
        
        # Full results
        reports["full_results.json"] = json.dumps({
            "plugin_to_api": results,
            "api_to_plugin": json_api_to_plugins
        }, indent=2)
        
        return reports
    
    def _generate_html(
        self,
        results: Dict[str, Dict[str, Dict[str, int]]],
        api_to_plugins: Dict[str, Dict[str, Set[str]]],
    ) -> str:
        """Generate an HTML report.
        
        Args:
            results: Analysis results.
            api_to_plugins: Mapping from API symbols to plugins.
            
        Returns:
            HTML report as a string.
        """
        # Convert results to pandas DataFrames for easy HTML conversion
        plugin_to_api_rows = []
        for api_version, plugins in results.items():
            for plugin_name, symbols in plugins.items():
                for symbol_name, count in symbols.items():
                    plugin_to_api_rows.append({
                        "API_Version": api_version,
                        "Plugin": plugin_name,
                        "Symbol": symbol_name,
                        "Occurrences": count
                    })
        
        api_to_plugin_rows = []
        for api_version, symbols in api_to_plugins.items():
            for symbol_name, plugin_set in symbols.items():
                api_to_plugin_rows.append({
                    "API_Version": api_version,
                    "Symbol": symbol_name,
                    "Plugin_Count": len(plugin_set),
                    "Plugins": ", ".join(sorted(plugin_set))
                })
        
        if not plugin_to_api_rows or not api_to_plugin_rows:
            return "<h1>No results to display</h1>"
        
        # Create DataFrames
        plugin_to_api_df = pd.DataFrame(plugin_to_api_rows)
        api_to_plugin_df = pd.DataFrame(api_to_plugin_rows)
        api_to_plugin_df = api_to_plugin_df.sort_values("Plugin_Count", ascending=False)
        
        # Create HTML
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>OpenCPN Plugin API Usage Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "table { border-collapse: collapse; margin: 10px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "tr:nth-child(even) { background-color: #f9f9f9; }",
            "h1, h2, h3 { color: #333; }",
            ".tab { overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; }",
            ".tab button { background-color: inherit; float: left; border: none; ",
            "outline: none; cursor: pointer; padding: 14px 16px; }",
            ".tab button:hover { background-color: #ddd; }",
            ".tab button.active { background-color: #ccc; }",
            ".tabcontent { display: none; padding: 6px 12px; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>OpenCPN Plugin API Usage Report</h1>",
            
            "<div class='tab'>",
            "<button class='tablinks' onclick=\"openTab(event, 'Summary')\">Summary</button>",
            "<button class='tablinks' onclick=\"openTab(event, 'APIpop')\" id='defaultOpen'>API Popularity</button>",
            "<button class='tablinks' onclick=\"openTab(event, 'PluginUsage')\">Plugin Usage</button>",
            "</div>",
            
            "<div id='Summary' class='tabcontent'>",
            f"<h2>Summary</h2>",
            f"<p>Total plugins analyzed: {len(set(row['Plugin'] for row in plugin_to_api_rows))}</p>",
            f"<p>Total API symbols used: {len(set(row['Symbol'] for row in plugin_to_api_rows))}</p>",
            f"<p>API versions: {', '.join(sorted(set(row['API_Version'] for row in plugin_to_api_rows)))}</p>",
            "</div>",
            
            "<div id='APIpop' class='tabcontent'>",
            "<h2>API Symbol Popularity</h2>",
            api_to_plugin_df.to_html(index=False),
            "</div>",
            
            "<div id='PluginUsage' class='tabcontent'>",
            "<h2>API Usage by Plugin</h2>",
            plugin_to_api_df.to_html(index=False),
            "</div>",
            
            "<script>",
            "function openTab(evt, tabName) {",
            "  var i, tabcontent, tablinks;",
            "  tabcontent = document.getElementsByClassName('tabcontent');",
            "  for (i = 0; i < tabcontent.length; i++) {",
            "    tabcontent[i].style.display = 'none';",
            "  }",
            "  tablinks = document.getElementsByClassName('tablinks');",
            "  for (i = 0; i < tablinks.length; i++) {",
            "    tablinks[i].className = tablinks[i].className.replace(' active', '');",
            "  }",
            "  document.getElementById(tabName).style.display = 'block';",
            "  evt.currentTarget.className += ' active';",
            "}",
            "document.getElementById('defaultOpen').click();",
            "</script>",
            "</body>",
            "</html>"
        ]
        
        return "\n".join(html)
    
    def generate(self, results: Dict[str, Dict[str, Dict[str, int]]]) -> None:
        """Generate reports from analysis results.
        
        Args:
            results: Analysis results.
        """
        self.logger.info(f"Generating {self.format} reports")
        
        # Generate API to plugin mapping
        api_to_plugins = self._generate_api_to_plugin_map(results)
        
        # Generate reports based on the specified format
        if self.format == "markdown":
            md_content = self._generate_markdown(results, api_to_plugins)
            md_path = self.output_dir / "report.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            self.logger.info(f"Markdown report saved to {md_path}")
        
        elif self.format == "csv":
            csv_reports = self._generate_csv(results, api_to_plugins)
            for file_name, content in csv_reports.items():
                csv_path = self.output_dir / file_name
                with open(csv_path, "w", encoding="utf-8") as f:
                    f.write(content)
            self.logger.info(f"CSV reports saved to {self.output_dir}")
        
        elif self.format == "json":
            json_reports = self._generate_json(results, api_to_plugins)
            for file_name, content in json_reports.items():
                json_path = self.output_dir / file_name
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(content)
            self.logger.info(f"JSON reports saved to {self.output_dir}")
        
        elif self.format == "html":
            html_content = self._generate_html(results, api_to_plugins)
            html_path = self.output_dir / "report.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info(f"HTML report saved to {html_path}")
        
        else:
            self.logger.error(f"Unsupported report format: {self.format}")
            raise ValueError(f"Unsupported report format: {self.format}")
        
        self.logger.info("Report generation complete")