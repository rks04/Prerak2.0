import re

FORBIDDEN_PATTERNS = [
    r"\bsource\b",
    r"\bapt-get\b",
    r"\bsudo\b",
    r"\brm -rf\b",
    r"\bchmod\b",
    r"/bin/",
]

class WindowsShellAdapter:
    @staticmethod
    def validate_command(command: str) -> str:
        """
        Validates the command against forbidden Linux/Unix patterns that 
        are known to fail on Windows or cause security issues.
        Returns the error string if forbidden, or None if valid.
        """
        cmd_lower = command.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, cmd_lower):
                return f"Command contains forbidden Windows pattern matching '{pattern}'. Do NOT use Linux bash syntax like source or /bin/."
        return None

    @staticmethod
    def normalize_command(command: str) -> str:
        """
        Simplifies chained commands or unnecessary venv activations.
        """
        # Basic simplification: if they try to use source venv/bin/activate, 
        # we could transform it, but since we reject it in validate_command, 
        # we rely on the agent to fix it.
        # However, we can strip unnecessary quotes or format it cleanly here.
        return command.strip()
