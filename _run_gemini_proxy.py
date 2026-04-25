import subprocess
import sys

# 绕过 UAC：后台专门用 subprocess 调 test_gemini_proxy.py
result = subprocess.run(
    ["python", "test/test_gemini_proxy.py"],
    check=False
)
sys.exit(result.returncode)
