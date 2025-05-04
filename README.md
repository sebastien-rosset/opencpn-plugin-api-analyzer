# OpenCPN Plugin API Analyzer

A tool to analyze API usage across OpenCPN plugins.

## Overview

This project automatically analyzes the API usage in OpenCPN plugins by:

1. Parsing the OpenCPN plugin API header file using Clang/LLVM
2. Extracting plugin metadata from the OpenCPN plugins XML file
3. Cloning plugin repositories and analyzing their source code
4. Generating reports of API usage across plugins

## Installation

```bash
# Install with Poetry
poetry install
```

## Usage

```bash
# Run the analyzer with default settings
poetry run analyze

# Run with specific options
poetry run analyze --output-dir ./reports --format html

# Get help on available options
poetry run analyze --help
```

## Features

- Uses Clang/LLVM for accurate C++ parsing
- Reduces false positives and negatives with sophisticated heuristics
- Automatically extracts API symbols from header files
- Supports multiple report formats (Markdown, HTML, CSV, JSON)