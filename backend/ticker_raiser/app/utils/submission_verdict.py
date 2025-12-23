"""
Submission verdict comparison utility for judge system.

Compares user code output against test case expected output with various strategies.
"""

from enum import Enum
from typing import Tuple
from app.utils.text_processor import compare_outputs


class VerdictType(Enum):
    """Submission verdict types"""
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    PENDING = "PENDING"


class ComparisonStrategy(Enum):
    """Output comparison strategies"""
    EXACT = "exact"              # Byte-for-byte comparison
    TRIM_TRAILING = "trim"       # Ignore trailing whitespace
    NORMALIZED = "normalized"    # Ignore all extra whitespace
    TOKEN = "token"              # Line-by-line token comparison


def compare_with_strategy(
    actual_output: str,
    expected_output: str,
    strategy: ComparisonStrategy = ComparisonStrategy.TRIM_TRAILING
) -> bool:
    """
    Compare outputs using specified strategy.
    
    Args:
        actual_output: Output from user's code
        expected_output: Expected output from test case
        strategy: Comparison mode
        
    Returns:
        True if outputs match according to strategy
    """
    if strategy == ComparisonStrategy.EXACT:
        return actual_output == expected_output
    
    elif strategy == ComparisonStrategy.TRIM_TRAILING:
        # Ignore trailing whitespace
        return actual_output.rstrip() == expected_output.rstrip()
    
    elif strategy == ComparisonStrategy.NORMALIZED:
        # Normalize all whitespace
        actual_lines = [line.split() for line in actual_output.strip().split('\n')]
        expected_lines = [line.split() for line in expected_output.strip().split('\n')]
        return actual_lines == expected_lines
    
    elif strategy == ComparisonStrategy.TOKEN:
        # Token-by-token comparison (ignores formatting)
        actual_tokens = actual_output.split()
        expected_tokens = expected_output.split()
        return actual_tokens == expected_tokens
    
    return False


def evaluate_submission(
    actual_output: str,
    expected_output: str,
    strategy: ComparisonStrategy = ComparisonStrategy.TRIM_TRAILING,
    timeout_occurred: bool = False,
    runtime_error: bool = False,
    error_message: str = None
) -> Tuple[VerdictType, str]:
    """
    Evaluate a submission against a test case.
    
    Args:
        actual_output: Output from user's code
        expected_output: Expected output
        strategy: How to compare outputs
        timeout_occurred: Whether code exceeded time limit
        runtime_error: Whether code had runtime error
        error_message: Error message if applicable
        
    Returns:
        Tuple of (VerdictType, message)
    """
    # Check for runtime errors first
    if runtime_error:
        return VerdictType.RUNTIME_ERROR, error_message or "Runtime error occurred"
    
    # Check for timeout
    if timeout_occurred:
        return VerdictType.TIME_LIMIT_EXCEEDED, "Time limit exceeded"
    
    # Check if outputs match
    if compare_with_strategy(actual_output, expected_output, strategy):
        return VerdictType.ACCEPTED, "Output matches expected"
    
    # If not matching, provide details
    return VerdictType.WRONG_ANSWER, (
        f"Expected:\n{expected_output}\n\n"
        f"Got:\n{actual_output}"
    )


def batch_evaluate_submission(
    actual_outputs: list[str],
    expected_outputs: list[str],
    strategy: ComparisonStrategy = ComparisonStrategy.TRIM_TRAILING,
    timeouts: list[bool] = None,
    runtime_errors: list[bool] = None
) -> dict:
    """
    Evaluate submission against multiple test cases.
    
    Args:
        actual_outputs: List of actual outputs (one per test case)
        expected_outputs: List of expected outputs
        strategy: Comparison strategy
        timeouts: List of boolean indicating timeout per test case
        runtime_errors: List of boolean indicating runtime error per test case
        
    Returns:
        Dictionary with results:
        {
            'passed': int,          # Number of passed test cases
            'total': int,           # Total test cases
            'verdict': VerdictType, # Overall verdict
            'details': list[dict]   # Per-test-case details
        }
    """
    timeouts = timeouts or [False] * len(actual_outputs)
    runtime_errors = runtime_errors or [False] * len(actual_outputs)
    
    details = []
    passed = 0
    first_failure = None
    
    for i, (actual, expected, timeout, error) in enumerate(
        zip(actual_outputs, expected_outputs, timeouts, runtime_errors)
    ):
        verdict, message = evaluate_submission(
            actual,
            expected,
            strategy,
            timeout,
            error
        )
        
        details.append({
            'test_case': i + 1,
            'verdict': verdict.value,
            'message': message
        })
        
        if verdict == VerdictType.ACCEPTED:
            passed += 1
        elif first_failure is None:
            first_failure = verdict
    
    # Determine overall verdict
    if first_failure:
        overall_verdict = first_failure
    elif passed == len(actual_outputs):
        overall_verdict = VerdictType.ACCEPTED
    else:
        overall_verdict = VerdictType.WRONG_ANSWER
    
    return {
        'passed': passed,
        'total': len(actual_outputs),
        'verdict': overall_verdict.value,
        'percentage': round((passed / len(actual_outputs) * 100), 2),
        'details': details
    }


# Example usage in judge worker
"""
from app.utils.submission_verdict import (
    batch_evaluate_submission,
    ComparisonStrategy,
    VerdictType
)
from app.models.models import Submission

# After running user's code
results = batch_evaluate_submission(
    actual_outputs=[output1, output2, output3],
    expected_outputs=[test1.expected_output, test2.expected_output, test3.expected_output],
    strategy=ComparisonStrategy.TRIM_TRAILING,
    timeouts=[False, False, False],
    runtime_errors=[False, False, False]
)

# Update submission
submission.status = results['verdict']
submission.test_cases_passed = results['passed']
submission.total_test_cases = results['total']
db.commit()
"""
