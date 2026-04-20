class ExecAdapter:
    SAFE_COMMANDS = {
        "echo": "echo output",
        "pwd": "/mock/workspace",
        "ls": "docs output",
    }

    def exec(self, command: str, cwd: str | None = None) -> dict:
        head = command.strip().split(" ")[0] if command.strip() else ""
        if head not in self.SAFE_COMMANDS:
            return {
                "simulated": True,
                "executed": False,
                "command": command,
                "cwd": cwd,
                "stdout": "",
                "stderr": "command not in safe simulation list",
                "returncode": 1,
            }
        return {
            "simulated": True,
            "executed": True,
            "command": command,
            "cwd": cwd,
            "stdout": self.SAFE_COMMANDS[head],
            "stderr": "",
            "returncode": 0,
        }
