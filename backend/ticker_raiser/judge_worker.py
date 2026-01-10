import redis
import time
import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.crud.submission import get_submission_by_id
from app.crud.problem import get_problem_by_id, get_test_cases_by_problem
from app.services.submission import SubmissionService

logger = get_logger("judge_worker")
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

DOCKER_IMAGE = "python:3.12-slim"

MAX_DOCKER_TIMEOUT = 30
CLEANUP_RETRY_DELAY = 1 


def cleanup_docker_container(container_id: str, max_retries: int = 3) -> bool:
    """
    Forcefully cleanup a Docker container with retries.
    
    Args:
        container_id: Container ID or name
        max_retries: Maximum number of cleanup attempts
    
    Returns:
        True if cleanup succeeded, False otherwise
    """
    for attempt in range(max_retries):
        try:
            subprocess.run(
                ["docker", "stop", "-t", "2", container_id],
                capture_output=True,
                timeout=5,
                check=False
            )
            
            result = subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True,
                timeout=5,
                check=False
            )
            
            if result.returncode == 0:
                logger.debug(f"Cleaned up container {container_id}")
                return True
            
            if "No such container" in result.stderr.decode():
                return True
            
            logger.warning(f"Cleanup attempt {attempt + 1} failed for {container_id}")
            time.sleep(CLEANUP_RETRY_DELAY)
        
        except Exception as e:
            logger.error(f"Cleanup error for {container_id}: {e}")
            time.sleep(CLEANUP_RETRY_DELAY)
    
    logger.error(f"Failed to cleanup container {container_id} after {max_retries} attempts")
    return False


def run_docker_judge(
    code: str,
    input_data: str,
    expected_output: str,
    time_limit_ms: int
) -> dict:
    """
    Run Python code in Docker container and compare output.
    Optimized version with better resource management.
    
    Returns:
        {
            "passed": bool,
            "actual_output": str,
            "error": str or None,
            "error_type": str or None,
            "timed_out": bool
        }
    """
    time_limit_sec = time_limit_ms / 1000
    docker_timeout = min(int(time_limit_sec) + 5, MAX_DOCKER_TIMEOUT)
    
    temp_dir = None
    temp_file = None
    container_id = None
    proc = None
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="judge_")
        temp_file = os.path.join(temp_dir, "solution.py")
        
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
        
        container_name = f"judge_{int(time.time() * 1000)}_{os.getpid()}"
        
        docker_cmd = [
            "docker", "run",
            "--name", container_name,  # Named for cleanup tracking
            "--rm",  # Auto-remove on exit
            "-i",  # Interactive (for stdin)
            "--network=none",  # No network access
            "--memory=256m",  # Memory limit
            "--memory-swap=256m",  # Disable swap
            "--cpus=1",  # CPU limit
            "--pids-limit=50",  # Limit processes
            "--ulimit", "nofile=64:64",  # Limit file descriptors
            "--read-only",  # Read-only root filesystem
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=50m",  # Temp space
            "-v", f"{temp_file}:/solution.py:ro",  # Mount code as read-only
            DOCKER_IMAGE,
            "timeout", str(int(time_limit_sec) + 1), "python", "/solution.py"
        ]
        
        logger.debug(f"Starting container: {container_name}")
        
        proc = subprocess.Popen(
            docker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        container_id = container_name
        
        start_time = time.time()
        try:
            stdout, stderr = proc.communicate(
                input=input_data,
                timeout=docker_timeout
            )
            execution_time = time.time() - start_time
            
            logger.debug(f"Execution completed in {execution_time:.2f}s")
        
        except subprocess.TimeoutExpired:
            logger.warning(f"TIMEOUT for {container_name} after {docker_timeout}s")
            
            try:
                proc.kill()
                proc.wait(timeout=2)
            except:
                pass
            
            cleanup_docker_container(container_name)
            
            return {
                "passed": False,
                "actual_output": "",
                "error": f"Time limit exceeded ({time_limit_ms}ms)",
                "error_type": "TIMEOUT",
                "timed_out": True
            }
        
        if proc.returncode != 0:
            error_msg = stderr.strip()[:500]  
            
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
            elif "MemoryError" in stderr:
                error_type = "MEMORY_LIMIT"
            elif "timed out" in stderr.lower():
                return {
                    "passed": False,
                    "actual_output": "",
                    "error": f"Time limit exceeded ({time_limit_ms}ms)",
                    "error_type": "TIMEOUT",
                    "timed_out": True
                }
            
            logger.debug(f"Runtime error: {error_type}")
            
            return {
                "passed": False,
                "actual_output": "",
                "error": error_msg,
                "error_type": error_type,
                "timed_out": False
            }
        
        # Compare output
        actual_output = stdout.strip()
        expected = expected_output.strip()
        passed = actual_output == expected
        
        if not passed:
            logger.debug(f"Wrong answer: expected='{expected}', got='{actual_output}'")
        
        return {
            "passed": passed,
            "actual_output": actual_output,
            "error": None,
            "error_type": "WRONG_ANSWER" if not passed else None,
            "timed_out": False
        }
    
    except Exception as e:
        logger.error(f"Judge error: {e}", exc_info=True)
        
        if container_id:
            cleanup_docker_container(container_id)
        
        return {
            "passed": False,
            "actual_output": "",
            "error": f"System error: {str(e)[:200]}",
            "error_type": "SYSTEM_ERROR",
            "timed_out": False
        }
    
    finally:
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except:
                pass
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")


def judge_submission(submission_id: int) -> bool:
    """
    Judge a single submission.
    
    Returns: True if judging succeeded, False if error
    """
    db = SessionLocal()
    
    try:
        submission = get_submission_by_id(db, submission_id)
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return False
        
        logger.info(f"Judging submission {submission_id} for problem {submission.problem_id}")
        
        problem = get_problem_by_id(db, submission.problem_id)
        if not problem:
            logger.error(f"Problem {submission.problem_id} not found")
            return False
        
        test_cases = get_test_cases_by_problem(db, problem.id)
        if not test_cases:
            logger.error(f"No test cases for problem {problem.id}")
            return False
        
        logger.info(f"Running {len(test_cases)} test cases (time limit: {problem.time_limit_ms}ms)")
        
        passed_count = 0
        final_status = "ACCEPTED"
        
        for i, test_case in enumerate(test_cases, 1):
            logger.debug(f"Test case {i}/{len(test_cases)}")
            
            result = run_docker_judge(
                code=submission.code,
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
                time_limit_ms=problem.time_limit_ms
            )
            
            if result["passed"]:
                logger.debug(f"✓ Test {i} PASSED")
                passed_count += 1
            elif result["timed_out"]:
                logger.warning(f" Test {i} TIME_LIMIT_EXCEEDED")
                final_status = "TIME_LIMIT_EXCEEDED"
                break  # Stop on first failure
            elif result["error"]:
                logger.warning(f" Test {i} RUNTIME_ERROR ({result['error_type']})")
                final_status = "RUNTIME_ERROR"
                break
            else:
                logger.warning(f" Test {i} WRONG_ANSWER")
                if final_status == "ACCEPTED":
                    final_status = "WRONG_ANSWER"
        
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


def cleanup_orphaned_containers():
    """Clean up any orphaned judge containers from previous runs."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=judge_", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            containers = result.stdout.strip().split("\n")
            logger.info(f"Found {len(containers)} orphaned containers, cleaning up...")
            
            for container in containers:
                cleanup_docker_container(container)
    
    except Exception as e:
        logger.warning(f"Failed to cleanup orphaned containers: {e}")


def worker_loop():
    """Main worker loop - blocks on Redis BRPOP"""
    logger.info("Judge worker starting...")
    
    try:
        redis_client.ping()
        logger.info("✓ Redis connected")
    except Exception as e:
        logger.error(f" Redis connection failed: {e}")
        logger.error("Make sure Redis is running: docker run -d --name redis -p 6379:6379 redis:7-alpine")
        sys.exit(1)
    
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False
        )
        if result.returncode != 0:
            logger.error(" Docker not available or not running")
            sys.exit(1)
        logger.info("✓ Docker available")
    except Exception as e:
        logger.error(f" Docker check failed: {e}")
        sys.exit(1)
    
    cleanup_orphaned_containers()
    
    logger.info("✓ Worker ready - listening for submissions...")
    
    while True:
        try:
            result = redis_client.brpop("submissions_queue", timeout=0)
            
            if result:
                submission_id = int(result[1])
                logger.info(f"Received submission {submission_id}")
                
                judge_submission(submission_id)
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            logger.info("Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    worker_loop()