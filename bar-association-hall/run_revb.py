"""Runner script - avoids PowerShell inline quoting issues."""
import subprocess, sys
result = subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parent / "generate_revised_v2.py")],
    capture_output=True, text=True, timeout=180
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RC:", result.returncode)
