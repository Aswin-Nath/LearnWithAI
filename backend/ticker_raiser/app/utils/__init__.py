"""Utility modules for the application"""

from app.utils.text_processor import (
    normalize_text,
    normalize_newlines,
    remove_bom,
    remove_non_ascii_spaces,
    validate_test_case_data,
    prepare_test_case_for_storage,
    compare_outputs,
    get_test_case_statistics,
    WhitespaceNormalizationMode,
)

from app.utils.submission_verdict import (
    evaluate_submission,
    batch_evaluate_submission,
    compare_with_strategy,
    VerdictType,
    ComparisonStrategy,
)

__all__ = [
    # Text Processing
    "normalize_text",
    "normalize_newlines",
    "remove_bom",
    "remove_non_ascii_spaces",
    "validate_test_case_data",
    "prepare_test_case_for_storage",
    "compare_outputs",
    "get_test_case_statistics",
    "WhitespaceNormalizationMode",
    # Submission Verdict
    "evaluate_submission",
    "batch_evaluate_submission",
    "compare_with_strategy",
    "VerdictType",
    "ComparisonStrategy",
]

