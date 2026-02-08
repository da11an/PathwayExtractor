"""
Configuration loader for PDF extraction settings.
Supports multiple PDF formats through JSON configuration files.
"""
import json
import importlib
from pathlib import Path
from typing import Dict, List, Any, Callable


class PageConfig:
    """Configuration for extracting a single page."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.page_index = config_dict["page_index"]
        self.label = config_dict["label"]
        self.parser_module_name = config_dict["parser_module"]
        self.parser_function_name = config_dict["parser_function"]
        self.test_function_name = config_dict.get("test_function", "test_row")
        
        # Extraction settings
        extraction = config_dict.get("extraction", {})
        self.target_header = extraction.get("target_header", "pw_contactname")
        # Store expected headers - use all of them if available, otherwise fall back to target_header
        expected_headers = extraction.get("expected_first_column_header", None)
        if expected_headers:
            self.expected_headers = expected_headers if isinstance(expected_headers, list) else [expected_headers]
        else:
            # Fallback to using target_header as a single-item list
            self.expected_headers = [self.target_header]
        # Store expected last column headers (optional)
        expected_last_headers = extraction.get("expected_last_column_header", None)
        if expected_last_headers:
            self.expected_last_headers = expected_last_headers if isinstance(expected_last_headers, list) else [expected_last_headers]
        else:
            self.expected_last_headers = None
        self.start_top = extraction.get("start_top", 177)
        self.max_shift = extraction.get("max_shift", 150)
        self.delta = extraction.get("delta", 20)
        self.header_height = extraction.get("header_height", 25)
        # Precise header row bounds (optional - if provided, use instead of fixed header_height)
        self.header_top = extraction.get("header_top", None)
        self.header_bottom = extraction.get("header_bottom", None)
        self.use_explicit_vertical_lines = extraction.get("use_explicit_vertical_lines", True)
        self.minimum_column_width = extraction.get("minimum_column_width", 17)
        # Left and right bounds (None means use full page width)
        self.left_bound = extraction.get("left_bound", None)
        self.right_bound = extraction.get("right_bound", None)
        
        # Lazy load parser functions
        self._parser_module = None
        self._parser_function = None
        self._test_function = None
    
    def get_parser_function(self) -> Callable:
        """Lazy load and return the parser function."""
        if self._parser_function is None:
            if self._parser_module is None:
                self._parser_module = importlib.import_module(self.parser_module_name)
            self._parser_function = getattr(self._parser_module, self.parser_function_name)
        return self._parser_function
    
    def get_test_function(self) -> Callable:
        """Lazy load and return the test function."""
        if self._test_function is None:
            if self._parser_module is None:
                self._parser_module = importlib.import_module(self.parser_module_name)
            self._test_function = getattr(self._parser_module, self.test_function_name)
        return self._test_function


class ExtractionConfig:
    """Configuration for PDF extraction format."""
    
    def __init__(self, config_path: str):
        """Load configuration from JSON file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        self.format_name = config_dict.get("format_name", "unknown")
        self.description = config_dict.get("description", "")
        self.pages = [PageConfig(page_config) for page_config in config_dict.get("pages", [])]
    
    def get_page_configs(self) -> List[PageConfig]:
        """Get list of page configurations."""
        return self.pages
    
    def get_page_config_by_index(self, page_index: int) -> PageConfig:
        """Get page configuration by zero-based page index."""
        for page_config in self.pages:
            if page_config.page_index == page_index:
                return page_config
        raise ValueError(f"Page index {page_index} not found in configuration")
    
    def get_page_config_by_label(self, label: str) -> PageConfig:
        """Get page configuration by label."""
        for page_config in self.pages:
            if page_config.label == label:
                return page_config
        raise ValueError(f"Label {label} not found in configuration")


def load_config(config_path: str = None) -> ExtractionConfig:
    """
    Load extraction configuration.
    
    Args:
        config_path: Path to config JSON file. If None, uses default format_v1.json
    
    Returns:
        ExtractionConfig object
    """
    if config_path is None:
        # Default to format_v1.json in configs directory
        config_dir = Path(__file__).parent / "configs"
        config_path = config_dir / "format_v2.json"
    
    return ExtractionConfig(str(config_path))
