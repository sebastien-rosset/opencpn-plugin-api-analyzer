"""XML parser module for handling the OpenCPN plugins XML file."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from lxml import etree


@dataclass
class Plugin:
    """Data class representing an OpenCPN plugin."""

    name: str
    version: str
    api_version: Optional[str] = None
    source_url: Optional[str] = None
    source_repo: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    open_source: bool = False


class XMLParser:
    """Parser for the OpenCPN plugins XML file."""

    def __init__(self, xml_url: str):
        """Initialize the XML parser.

        Args:
            xml_url: URL or path to the XML file.
        """
        self.xml_url = xml_url
        self.logger = logging.getLogger(__name__)

    def _fetch_xml(self) -> bytes:
        """Fetch the XML content.

        Returns:
            XML content as bytes.

        Raises:
            ValueError: If the XML content couldn't be fetched.
        """
        self.logger.info(f"Fetching XML content from {self.xml_url}")

        if self.xml_url.startswith(("http://", "https://")):
            response = requests.get(self.xml_url, timeout=60)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch XML: {response.status_code}")
            return response.content

        # If it's a local file
        with open(self.xml_url, "rb") as f:
            return f.read()

    def _parse_git_url(self, url: str) -> Optional[str]:
        """Extract repository URL from a git URL.

        Args:
            url: Git repository URL.

        Returns:
            Normalized GitHub repository URL or None if not a valid GitHub URL.
        """
        if not url:
            return None

        url = url.strip()
        parsed = urlparse(url)

        # Handle GitHub URLs
        if "github.com" in parsed.netloc:
            path = parsed.path.strip("/")

            # Remove .git suffix if present
            if path.endswith(".git"):
                path = path[:-4]

            return f"https://github.com/{path}"

        # For other git hosting services, just return the original URL for now
        return url

    def parse(self) -> Dict[str, Plugin]:
        """Parse the OpenCPN plugins XML file.

        Returns:
            Dictionary mapping plugin names to Plugin objects.
        """
        self.logger.info("Parsing OpenCPN plugins XML file")
        xml_content = self._fetch_xml()

        root = etree.fromstring(xml_content)
        plugins = {}

        for plugin_elem in root.findall(".//plugin"):
            try:
                name_elem = plugin_elem.find("name")
                if name_elem is None or not name_elem.text:
                    self.logger.warning("Found plugin without name, skipping")
                    continue

                name = name_elem.text.strip()

                version_elem = plugin_elem.find("version")
                version = (
                    version_elem.text.strip()
                    if version_elem is not None and version_elem.text
                    else "unknown"
                )

                api_version_elem = plugin_elem.find("api-version")
                api_version = (
                    api_version_elem.text.strip()
                    if api_version_elem is not None and api_version_elem.text
                    else None
                )

                source_elem = plugin_elem.find("source")
                source_url = (
                    source_elem.text.strip()
                    if source_elem is not None and source_elem.text
                    else None
                )
                source_repo = self._parse_git_url(source_url)

                summary_elem = plugin_elem.find("summary")
                summary = (
                    summary_elem.text.strip()
                    if summary_elem is not None and summary_elem.text
                    else None
                )

                desc_elem = plugin_elem.find("description")
                description = (
                    desc_elem.text.strip()
                    if desc_elem is not None and desc_elem.text
                    else None
                )

                author_elem = plugin_elem.find("author")
                author = (
                    author_elem.text.strip()
                    if author_elem is not None and author_elem.text
                    else None
                )

                open_source_elem = plugin_elem.find("open-source")
                open_source = (
                    open_source_elem is not None
                    and open_source_elem.text
                    and open_source_elem.text.strip().lower() == "yes"
                )

                plugin = Plugin(
                    name=name,
                    version=version,
                    api_version=api_version,
                    source_url=source_url,
                    source_repo=source_repo,
                    summary=summary,
                    description=description,
                    author=author,
                    open_source=open_source,
                )

                plugins[name] = plugin
                self.logger.debug(f"Parsed plugin: {name} (version: {version})")

            except Exception as e:
                self.logger.error(f"Error parsing plugin: {e}")

        self.logger.info(f"Parsed {len(plugins)} plugins")
        return plugins
