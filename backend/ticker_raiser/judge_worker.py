#!/usr/bin/env python3
"""
Judge Worker - Main Loop
Polls Redis for submissions and executes judge logic

Architecture:
1. BRPOP submissions_queue (blocking)
2. Fetch submission + problem + test_cases from DB
3. Run Docker judge (Python only)
4. Update DB with results
5. Loop back to BRPOP
"""

import redis
import time
import sys
import os
import subprocess
import tempfile

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.crud.submission import get_submission_by_id
from app.crud.problem import get_problem_by_id, get_test_cases_by_problem
from app.services.submission import SubmissionService

# Setup logging
logger = get_logger("judge_worker")

# Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Docker image for Python
DOCKER_IMAGE = "python:3.12-slim"


def run_docker_judge(
    code: str,
    input_data: str,
    expected_output: str,
    time_limit_ms: int
) -> dict:
    """
    Run Python code in Docker container and compare output.
    Hardened version with proper cleanup and timeout handling.
    
    Returns:
        {
            "passed": bool,
            "actual_output": str,
            "error": str or None,
            "error_type": "TIMEOUT" | "RUNTIME" | "WRONG_ANSWER",
            "timed_out": bool
        }
    """
    time_limit_sec = time_limit_ms / 1000
    temp_file = None
    proc = None
    
    try:
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        docker_cmd = [
            "docker", "run", "-i", "--rm",
            "--memory=256m",
            "--cpus=1",
            "-v", f"{temp_file}:/tmp/solution.py:ro",
            DOCKER_IMAGE,
            "python", "/tmp/solution.py"
        ]
        
        # Spawn process
        proc = subprocess.Popen(
            docker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Communicate with process
        try:
            stdout, stderr = proc.communicate(
                input=input_data, 
                timeout=int(time_limit_sec) + 5
            )
        except subprocess.TimeoutExpired:
            # Strict timeout kill
            logger.warning(f"TIMEOUT - killing process {proc.pid}")
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.error(f"FORCE KILL on PID {proc.pid}")
                proc.kill()
            
            return {
                "passed": False,
                "actual_output": "",
                "error": "Time limit exceeded",
                "error_type": "TIMEOUT",
                "timed_out": True
            }
        
        # Check output
        actual_output = stdout.strip()
        expected = expected_output.strip()
        
        # Classify errors
        if proc.returncode != 0:
            # Extract error type from stderr
            error_type = "RUNTIME"
            if "SyntaxError" in stderr:
                error_type = "SYNTAX_ERROR"
            elif "NameError" in stderr:
                error_type = "NAME_ERROR"
            elif "TypeError" in stderr:
                error_type = "TYPE_ERROR"
            elif "ValueError" in stderr:
                error_type = "VALUE_ERROR"
            elif "IndexError" in stderr:
                error_type = "INDEX_ERROR"
            elif "ZeroDivisionError" in stderr:
                error_type = "ZERO_DIVISION"
            
            return {
                "passed": False,
                "actual_output": "",
                "error": stderr[:200],  # Truncate long errors
                "error_type": error_type,
                "timed_out": False
            }
        
        return {
            "passed": actual_output == expected,
            "actual_output": actual_output,
            "error": None,
            "error_type": "WRONG_ANSWER" if actual_output != expected else None,
            "timed_out": False
        }
    
    except Exception as e:
        return {
            "passed": False,
            "actual_output": "",
            "error": str(e)[:200],
            "error_type": "RUNTIME",
            "timed_out": False
        }
    
    finally:
        # Strict cleanup
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except:
                pass
        
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception as e:
                print(f"    [DEBUG] Failed to cleanup {temp_file}: {e}")


def judge_submission(submission_id: int) -> bool:
    """
    Judge a single submission.
    
    Returns: True if judging succeeded, False if error
    """
    db = SessionLocal()
    
    try:
        # Fetch submission
        submission = get_submission_by_id(db, submission_id)
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return False
        
        logger.info(f"Judging submission {submission_id}")
        
        # Fetch problem
        problem = get_problem_by_id(db, submission.problem_id)
        if not problem:
            logger.error(f"Problem {submission.problem_id} not found")
            return False
        
        logger.debug(f"Problem: {problem.title}, Time limit: {problem.time_limit_ms}ms")
        
        # Fetch test cases
        test_cases = get_test_cases_by_problem(db, problem.id)
        if not test_cases:
            logger.error(f"No test cases for problem {problem.id}")
            return False
        
        logger.debug(f"Found {len(test_cases)} test cases")
        
        # Judge each test case
        passed_count = 0
        final_status = "ACCEPTED"
        
        for i, test_case in enumerate(test_cases):
            logger.debug(f"Testing case {i+1}/{len(test_cases)}")
            
            result = run_docker_judge(
                code=submission.code,
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
                time_limit_ms=problem.time_limit_ms
            )
            
            if result["passed"]:
                logger.debug(f"Test case {i+1}: PASSED")
                passed_count += 1
            elif result["timed_out"]:
                logger.warning(f"Test case {i+1}: TIME_LIMIT_EXCEEDED")
                final_status = "TIME_LIMIT_EXCEEDED"
                break
            elif result["error"]:
                logger.warning(f"Test case {i+1}: RUNTIME_ERROR - {result['error_type']}")
                final_status = "RUNTIME_ERROR"
                break
            else:
                logger.warning(f"Test case {i+1}: WRONG_ANSWER")
                if final_status == "ACCEPTED":
                    final_status = "WRONG_ANSWER"
        
        # Update submission in DB
        SubmissionService.update_submission_after_judge(
            db=db,
            submission_id=submission_id,
            status=final_status,
            test_cases_passed=passed_count
        )
        
        logger.info(f"Submission {submission_id}: {final_status} ({passed_count}/{len(test_cases)})")
        return True
    
    except Exception as e:
        logger.error(f"Error judging submission {submission_id}: {e}", exc_info=True)
        try:
            SubmissionService.update_submission_after_judge(
                db=db,
                submission_id=submission_id,
                status="RUNTIME_ERROR",
                test_cases_passed=0
            )
        except Exception as db_error:
            logger.error(f"Failed to update submission status: {db_error}")
        return False
    
    finally:
        db.close()


def worker_loop():
    """Main worker loop - blocks on Redis BRPOP"""
    logger.info("Judge worker started")
    
    # Check Redis connection
    try:
        redis_client.ping()
        logger.info("Redis connected (port 6379)")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.error("Make sure Redis is running: docker run -d --name redis -p 6379:6379 redis:7-alpine")
        sys.exit(1)
    
    logger.info("Listening for submissions on Redis queue...")
    
    while True:
        try:
            # BRPOP blocks until submission arrives (timeout=0 means infinite)
            result = redis_client.brpop("submissions_queue", timeout=0)
            
            if result:
                submission_id = int(result[1])
                judge_submission(submission_id)
        
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    worker_loop()
