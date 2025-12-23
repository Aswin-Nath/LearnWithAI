"""
Database migration script to clean up existing test case data.

This script normalizes all existing test cases in the database by:
1. Removing non-ASCII spaces and other Unicode whitespace
2. Normalizing line endings to \n
3. Trimming trailing spaces from lines
4. Fixing any BOM markers

Usage:
    python -m app.migrations.normalize_test_cases
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import TestCase
from app.utils.text_processor import (
    prepare_test_case_for_storage,
    WhitespaceNormalizationMode,
)


def migrate_test_cases_normalize() -> None:
    """
    Migrate all existing test cases to normalized format.
    
    This reads each test case, normalizes it, and updates the database.
    """
    db: Session = SessionLocal()
    
    try:
        # Get all test cases
        test_cases = db.query(TestCase).all()
        
        if not test_cases:
            print("✓ No test cases to migrate")
            return
        
        print(f"Found {len(test_cases)} test cases to migrate...")
        
        updated_count = 0
        error_count = 0
        
        for tc in test_cases:
            try:
                # Prepare test case data
                clean_input, clean_output, error_msg = prepare_test_case_for_storage(
                    tc.input_data,
                    tc.expected_output,
                    normalize=True,
                    normalization_mode=WhitespaceNormalizationMode.TRIM_LINES
                )
                
                if error_msg:
                    print(f"✗ Test case {tc.id}: {error_msg}")
                    error_count += 1
                    continue
                
                # Check if data actually changed
                if tc.input_data != clean_input or tc.expected_output != clean_output:
                    tc.input_data = clean_input
                    tc.expected_output = clean_output
                    updated_count += 1
                    
                    input_diff = "↵" if '\n' in clean_input else ""
                    output_diff = "↵" if '\n' in clean_output else ""
                    print(f"✓ Test case {tc.id}: Updated{' ' + input_diff if input_diff else ''}{' ' + output_diff if output_diff else ''}")
            
            except Exception as e:
                print(f"✗ Test case {tc.id}: {str(e)}")
                error_count += 1
        
        # Commit all changes
        if updated_count > 0:
            db.commit()
            print(f"\n✓ Migration complete: {updated_count} test cases updated, {error_count} errors")
        else:
            print("\n✓ All test cases already normalized")
    
    except Exception as e:
        db.rollback()
        print(f"\n✗ Migration failed: {str(e)}")
        raise
    
    finally:
        db.close()


if __name__ == "__main__":
    migrate_test_cases_normalize()
