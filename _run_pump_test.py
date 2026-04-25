import subprocess
import sys

result = subprocess.run(
    ["python", "test/test_pump_10s.py"],
    check=False,
)
sys.exit(result.returncode)
