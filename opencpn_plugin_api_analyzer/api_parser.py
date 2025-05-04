"""Parser for the OpenCPN plugin API header file using Clang."""

import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

# Import clang carefully with enhanced error handling
try:
    import clang.cindex
    from clang.cindex import Config
except ImportError as e:
    print(f"Error importing clang: {e}")
    print("Please make sure libclang-dev is installed on your system")
    sys.exit(1)

# Global flag to track if libclang has been initialized
_LIBCLANG_INITIALIZED = False


@dataclass
class ApiSymbol:
    """Data class representing an API symbol."""

    name: str
    kind: str
    location: str
    signature: Optional[str] = None
    comment: Optional[str] = None
    parent: Optional[str] = None


class ApiHeaderParser:
    """Parser for the OpenCPN plugin API header file."""

    def __init__(self, header_url: str):
        """Initialize the API header parser.

        Args:
            header_url: URL or path to the OpenCPN plugin API header file.
        """
        self.header_url = header_url
        self.logger = logging.getLogger(__name__)
        self.header_content = None
        self.header_path = None
        self.index = None

        # Initialize Clang once for the application
        global _LIBCLANG_INITIALIZED
        if not _LIBCLANG_INITIALIZED:
            self._initialize_clang()
            _LIBCLANG_INITIALIZED = True

        # Create Clang index
        self.index = clang.cindex.Index.create()

    def _initialize_clang(self):
        """Initialize the Clang library once."""
        lib_path = self._find_clang_lib_path()
        if lib_path:
            try:
                Config.set_library_path(lib_path)
                self.logger.info(f"Initialized libclang with library path: {lib_path}")
            except Exception as e:
                self.logger.warning(f"Failed to set libclang library path: {e}")
                self._try_direct_library_file()

    def _try_direct_library_file(self):
        """Try to set the library file directly if setting the path fails."""
        # Check common locations for the actual library file
        possible_library_files = [
            "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/libclang.dylib",
            "/opt/homebrew/opt/llvm/lib/libclang.dylib",
            "/usr/local/opt/llvm/lib/libclang.dylib",
        ]

        for lib_file in possible_library_files:
            if os.path.exists(lib_file):
                try:
                    Config.set_library_file(lib_file)
                    self.logger.info(f"Set libclang library file directly: {lib_file}")
                    return True
                except Exception as e:
                    self.logger.warning(f"Failed to set library file {lib_file}: {e}")

        self.logger.error("Could not initialize libclang with any known library file")
        return False

    def _find_clang_lib_path(self) -> str:
        """Find the path to the Clang library.

        Returns:
            Path to the Clang library.

        Raises:
            RuntimeError: If the Clang library path couldn't be found.
        """
        self.logger.info("Searching for libclang library...")

        # Check if LLVM is installed via Homebrew on macOS
        try:
            if sys.platform == "darwin":  # macOS
                # Try to find Homebrew's LLVM installation
                homebrew_paths = [
                    "/opt/homebrew/opt/llvm/lib",  # Apple Silicon
                    "/usr/local/opt/llvm/lib",  # Intel Mac
                ]

                for path in homebrew_paths:
                    lib_path = os.path.join(path, "libclang.dylib")
                    if os.path.exists(lib_path):
                        self.logger.info(f"Found libclang at Homebrew path: {lib_path}")
                        Config.set_library_file(lib_path)
                        return path

                # If Homebrew paths don't work, try using xcrun to find the system clang
                try:
                    xcrun_output = subprocess.check_output(
                        ["xcrun", "--find", "clang"], universal_newlines=True
                    ).strip()

                    # Get the directory containing clang
                    clang_dir = os.path.dirname(xcrun_output)
                    # Look for libclang in nearby directories
                    potential_dirs = [
                        os.path.join(os.path.dirname(clang_dir), "lib"),
                        # Go up one more directory and check lib
                        os.path.join(
                            os.path.dirname(os.path.dirname(clang_dir)), "lib"
                        ),
                    ]

                    for lib_dir in potential_dirs:
                        for lib_name in ["libclang.dylib", "libclang.so"]:
                            lib_path = os.path.join(lib_dir, lib_name)
                            if os.path.exists(lib_path):
                                self.logger.info(
                                    f"Found libclang via xcrun at: {lib_path}"
                                )
                                Config.set_library_file(lib_path)
                                return lib_dir
                except (subprocess.SubprocessError, FileNotFoundError):
                    self.logger.warning("Failed to locate clang using xcrun")
        except Exception as e:
            self.logger.warning(f"Error while searching for libclang on macOS: {e}")

        # Common paths on different operating systems
        possible_paths = [
            "/usr/lib/llvm-16/lib",
            "/usr/lib/llvm-15/lib",
            "/usr/lib/llvm-14/lib",
            "/usr/lib/llvm-13/lib",
            "/usr/lib/llvm-12/lib",
            "/usr/lib/llvm-11/lib",
            "/usr/lib/llvm-10/lib",
            "/usr/local/opt/llvm/lib",  # Homebrew on macOS
            "/opt/homebrew/opt/llvm/lib",  # Homebrew on Apple Silicon
            "/usr/local/lib",  # Common location on Unix-like systems
            # Add more common paths here
        ]

        for path in possible_paths:
            if os.path.exists(path):
                for lib_name in ["libclang.so", "libclang.dylib", "libclang.dll"]:
                    lib_path = os.path.join(path, lib_name)
                    if os.path.exists(lib_path):
                        self.logger.info(f"Found libclang at: {lib_path}")
                        Config.set_library_file(lib_path)
                        return path

        # Try to use the one installed with the Python package
        try:
            import clang

            clang_path = os.path.dirname(clang.__file__)
            self.logger.info(f"Using clang package path: {clang_path}")
            return clang_path
        except (ImportError, AttributeError):
            pass

        # If we reach this point, we couldn't find the library
        self.logger.error(
            "Couldn't find libclang. Please install LLVM and update your PATH, "
            "or manually set the path with clang.cindex.Config.set_library_path()"
        )

        # For macOS users, provide specific installation instructions
        if sys.platform == "darwin":
            self.logger.error(
                "\nOn macOS, you can install LLVM with Homebrew: `brew install llvm`\n"
                "After installation, you can set the path manually:\n"
                "from clang.cindex import Config\n"
                "Config.set_library_file('/opt/homebrew/opt/llvm/lib/libclang.dylib')  # for Apple Silicon\n"
                "or\n"
                "Config.set_library_file('/usr/local/opt/llvm/lib/libclang.dylib')  # for Intel Mac"
            )

        # Continue anyway with an empty path - maybe Python can find it via standard mechanism
        return ""

    def _fetch_header(self) -> str:
        """Fetch the header content.

        Returns:
            Path to the header file (can be a temporary file).

        Raises:
            ValueError: If the header file couldn't be fetched.
        """
        self.logger.info(f"Fetching header content from {self.header_url}")

        if self.header_path is not None:
            return self.header_path

        if self.header_url.startswith(("http://", "https://")):
            response = requests.get(self.header_url, timeout=60)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch header: {response.status_code}")

            self.header_content = response.text

            # Save to a temporary file
            fd, temp_file = tempfile.mkstemp(suffix=".h")
            os.write(fd, self.header_content.encode("utf-8"))
            os.close(fd)

            self.header_path = temp_file
            return self.header_path

        # If it's a local file
        self.header_path = self.header_url
        with open(self.header_path, "r", encoding="utf-8") as f:
            self.header_content = f.read()

        return self.header_path

    def _parse_comment(self, node) -> Optional[str]:
        """Parse a comment from a Clang node.

        Args:
            node: A Clang node.

        Returns:
            The comment text or None if no comment was found.
        """
        if not hasattr(node, "extent") or not node.extent:
            return None

        # Get raw source at the node's location
        start_line = node.extent.start.line - 1  # 0-based
        end_line = node.extent.end.line

        if not self.header_content:
            return None

        lines = self.header_content.splitlines()
        if start_line <= 0:
            return None

        # Look for comments in lines preceding the node
        comment_lines = []
        line_idx = start_line - 1

        # Go back up to 5 lines to look for comments
        for _ in range(min(5, line_idx + 1)):
            line = lines[line_idx].strip()
            if line.startswith("//"):
                comment_lines.insert(0, line[2:].strip())
            elif line.startswith("/*") or line.endswith("*/"):
                break
            elif not line:
                # Empty line breaks comment continuity
                if comment_lines:
                    break
            else:
                break
            line_idx -= 1

        if comment_lines:
            return "\n".join(comment_lines)

        return None

    def _get_signature(self, node) -> Optional[str]:
        """Get the signature of a function or method.

        Args:
            node: A Clang cursor node.

        Returns:
            The signature as a string or None if not applicable.
        """
        if node.kind in (
            clang.cindex.CursorKind.FUNCTION_DECL,
            clang.cindex.CursorKind.CXX_METHOD,
            clang.cindex.CursorKind.CONSTRUCTOR,
            clang.cindex.CursorKind.DESTRUCTOR,
            clang.cindex.CursorKind.FUNCTION_TEMPLATE,
        ):
            if self.header_content:
                # Get raw source at the node's location
                start_offset = node.extent.start.offset
                end_offset = node.extent.end.offset

                # Extract the relevant part of the source
                if 0 <= start_offset < end_offset <= len(self.header_content):
                    raw_sig = self.header_content[start_offset:end_offset]
                    # Remove any trailing statements
                    raw_sig = re.sub(r"\{.*\}", "", raw_sig, flags=re.DOTALL)
                    return raw_sig.strip()

        return None

    def _get_full_name(self, node) -> str:
        """Get the fully qualified name of a node.

        Args:
            node: A Clang cursor node.

        Returns:
            The fully qualified name as a string.
        """
        if node.kind == clang.cindex.CursorKind.TRANSLATION_UNIT:
            return ""

        parent = node.semantic_parent
        parent_name = self._get_full_name(parent) if parent else ""

        if (
            parent_name
            and node.kind != clang.cindex.CursorKind.NAMESPACE
            and parent.kind != clang.cindex.CursorKind.NAMESPACE
        ):
            return f"{parent_name}::{node.spelling}"

        return f"{parent_name}::{node.spelling}" if parent_name else node.spelling

    def _get_parent_name(self, node) -> Optional[str]:
        """Get the name of the node's parent.

        Args:
            node: A Clang cursor node.

        Returns:
            The parent's name or None if no parent.
        """
        parent = node.semantic_parent
        if parent and parent.kind != clang.cindex.CursorKind.TRANSLATION_UNIT:
            return self._get_full_name(parent)
        return None

    def _should_include_node(self, node) -> bool:
        """Determine if a node should be included in the API definition.

        Args:
            node: A Clang cursor node.

        Returns:
            True if the node should be included, False otherwise.
        """
        # Include most declarations and definitions
        if node.kind in (
            clang.cindex.CursorKind.FUNCTION_DECL,
            clang.cindex.CursorKind.CXX_METHOD,
            clang.cindex.CursorKind.CONSTRUCTOR,
            clang.cindex.CursorKind.DESTRUCTOR,
            clang.cindex.CursorKind.CLASS_DECL,
            clang.cindex.CursorKind.STRUCT_DECL,
            clang.cindex.CursorKind.ENUM_DECL,
            clang.cindex.CursorKind.TYPEDEF_DECL,
            clang.cindex.CursorKind.FIELD_DECL,
            clang.cindex.CursorKind.VAR_DECL,
            clang.cindex.CursorKind.ENUM_CONSTANT_DECL,
            clang.cindex.CursorKind.MACRO_DEFINITION,
        ):
            # Ensure the node is from the main file, not an included file
            return node.location.file and node.location.file.name == self.header_path

        return False

    def _process_node(self, node, symbols: Dict[str, ApiSymbol]) -> None:
        """Process a node and its children recursively.

        Args:
            node: A Clang cursor node.
            symbols: Dictionary of API symbols to update.
        """
        if self._should_include_node(node):
            name = self._get_full_name(node)
            if not name:
                return

            kind = node.kind.name
            location = f"{node.location.file.name}:{node.location.line}"
            signature = self._get_signature(node)
            comment = self._parse_comment(node)
            parent = self._get_parent_name(node)

            symbols[name] = ApiSymbol(
                name=name,
                kind=kind,
                location=location,
                signature=signature,
                comment=comment,
                parent=parent,
            )

        # Process children recursively
        for child in node.get_children():
            self._process_node(child, symbols)

    def parse(self) -> Dict[str, ApiSymbol]:
        """Parse the OpenCPN plugin API header file.

        Returns:
            Dictionary mapping symbol names to ApiSymbol objects.
        """
        self.logger.info("Parsing OpenCPN plugin API header file")

        header_path = self._fetch_header()
        self.logger.info(f"Parsing header file: {header_path}")

        # Parse the header file with Clang
        translation_unit = self.index.parse(
            header_path,
            args=["-xc++", "-std=c++11"],
            options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )

        # Process the translation unit
        symbols = {}
        self._process_node(translation_unit.cursor, symbols)

        self.logger.info(f"Found {len(symbols)} API symbols")
        return symbols
