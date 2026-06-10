import difflib

class PatchEngine:
    @staticmethod
    def generate_diff(path: str, before: str, after: str) -> str:
        """
        Generates a unified diff comparing before and after strings.
        Returns the diff as a single structured string patch.
        """
        if before == after:
            return ""

        before_lines = before.splitlines(keepends=True) if before else []
        after_lines = after.splitlines(keepends=True) if after else []

        # If files don't end with a newline, difflib might not handle it perfectly in all viewers,
        # but unified_diff is generally robust.
        
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3  # Context lines
        )
        
        return "".join(diff)

patch_engine = PatchEngine()
