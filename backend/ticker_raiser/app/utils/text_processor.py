"""
Advanced text processing utilities for storing raw test case data.

This module provides robust text handling with normalization, validation,
and preservation of meaningful whitespace.
"""

import re
import unicodedata
from typing import Tuple
from enum import Enum


class WhitespaceNormalizationMode(Enum):
    """Whitespace normalization strategies"""
    STRICT = "strict"  # Only normalize line endings, preserve internal spaces
    TRIM_LINES = "trim_lines"  # Trim trailing spaces from each line
    COMPACT = "compact"  # Normalize all consecutive spaces


def normalize_newlines(text: str) -> str:
    """
    Normalize various newline formats to standard \n.
    Handles: \r\n (Windows), \r (Mac), \n (Unix)
    
    Args:
        text: Raw input text
        
    Returns:
        Text with normalized newlines
    """
    # Convert Windows line endings to Unix
    text = text.replace('\r\n', '\n')
    # Convert old Mac line endings to Unix
    text = text.replace('\r', '\n')
    return text


def remove_bom(text: str) -> str:
    """
    Remove Byte Order Mark (BOM) if present.
    BOM can be inadvertently added when reading files.
    
    Args:
        text: Input text
        
    Returns:
        Text without BOM
    """
    if text.startswith('\ufeff'):
        text = text[1:]
    return text


def remove_non_ascii_spaces(text: str) -> str:
    """
    Replace non-ASCII space characters with regular ASCII space.
    Handles: non-breaking space (\u00A0), em-space, en-space, etc.
    
    Args:
        text: Input text
        
    Returns:
        Text with ASCII spaces only
    """
    # Unicode whitespace categories: Zs (separator, space), Zl, Zp
    result = []
    for char in text:
        if unicodedata.category(char) in ('Zs', 'Zl', 'Zp') and char != ' ':
            result.append(' ')
        else:
            result.append(char)
    return ''.join(result)


def normalize_text(
    text: str,
    mode: WhitespaceNormalizationMode = WhitespaceNormalizationMode.TRIM_LINES,
    strip_edges: bool = True
) -> str:
    """
    Comprehensive text normalization.
    
    Args:
        text: Raw input text
        mode: Normalization strategy
        strip_edges: Remove leading/trailing whitespace from entire text
        
    Returns:
        Normalized text preserving semantic content
    """
    if not text:
        return ""
    
    # Step 1: Remove BOM
    text = remove_bom(text)
    
    # Step 2: Normalize Unicode spaces
    text = remove_non_ascii_spaces(text)
    
    # Step 3: Normalize newlines
    text = normalize_newlines(text)
    
    # Step 4: Apply whitespace normalization strategy
    if mode == WhitespaceNormalizationMode.STRICT:
        # Keep everything as-is after newline normalization
        pass
    elif mode == WhitespaceNormalizationMode.TRIM_LINES:
        # Remove trailing spaces from each line
        lines = text.split('\n')
        lines = [line.rstrip(' \t') for line in lines]
        text = '\n'.join(lines)
    elif mode == WhitespaceNormalizationMode.COMPACT:
        # Normalize consecutive spaces (but preserve newlines)
        lines = text.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
        text = '\n'.join(lines)
    
    # Step 5: Edge trimming
    if strip_edges:
        text = text.strip()
    
    return text


def validate_test_case_data(input_data: str, expected_output: str) -> Tuple[bool, str]:
    """
    Validate test case data for integrity and storage readiness.
    
    Args:
        input_data: Test case input
        expected_output: Expected output
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not input_data or not isinstance(input_data, str):
        return False, "Input data must be a non-empty string"
    
    if not expected_output or not isinstance(expected_output, str):
        return False, "Expected output must be a non-empty string"
    
    # Check for null bytes (can cause issues in some systems)
    if '\0' in input_data or '\0' in expected_output:
        return False, "Input contains null bytes"
    
    # Check for valid encoding (all characters are UTF-8 compatible)
    try:
        input_data.encode('utf-8')
        expected_output.encode('utf-8')
    except UnicodeEncodeError as e:
        return False, f"Invalid UTF-8 encoding: {str(e)}"
    
    return True, ""


def prepare_test_case_for_storage(
    input_data: str,
    expected_output: str,
    normalize: bool = True,
    normalization_mode: WhitespaceNormalizationMode = WhitespaceNormalizationMode.TRIM_LINES
) -> Tuple[str, str, str]:
    """
    Prepare test case data for database storage with full validation.
    
    Args:
        input_data: Raw input data
        expected_output: Raw expected output
        normalize: Whether to normalize the text
        normalization_mode: Normalization strategy
        
    Returns:
        Tuple of (normalized_input, normalized_output, error_message)
        If error_message is empty, data is valid and ready for storage
    """
    # Validate first
    is_valid, error_msg = validate_test_case_data(input_data, expected_output)
    if not is_valid:
        return "", "", error_msg
    
    # Normalize if requested
    if normalize:
        input_data = normalize_text(input_data, mode=normalization_mode)
        expected_output = normalize_text(expected_output, mode=normalization_mode)
    
    return input_data, expected_output, ""


def compare_outputs(actual: str, expected: str, strict: bool = True) -> bool:
    """
    Compare actual output with expected output.
    
    Args:
        actual: Actual output from code execution
        expected: Expected output from test case
        strict: If False, ignores trailing whitespace differences
        
    Returns:
        True if outputs match according to comparison mode
    """
    if strict:
        return actual == expected
    else:
        # Strip trailing whitespace for comparison
        return actual.rstrip() == expected.rstrip()


def get_test_case_statistics(input_data: str, expected_output: str) -> dict:
    """
    Get statistics about test case data.
    
    Args:
        input_data: Test input
        expected_output: Expected output
        
    Returns:
        Dictionary with statistics
    """
    return {
        "input_lines": len(input_data.split('\n')),
        "input_chars": len(input_data),
        "input_bytes": len(input_data.encode('utf-8')),
        "output_lines": len(expected_output.split('\n')),
        "output_chars": len(expected_output),
        "output_bytes": len(expected_output.encode('utf-8')),
        "has_unicode": any(ord(c) > 127 for c in input_data + expected_output),
    }
