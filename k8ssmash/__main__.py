import os
import sys

# The render scale decides every surface size at import time, so it is read before the game modules load.
for _i, _arg in enumerate(sys.argv):
    if _arg == "--render-scale" and _i + 1 < len(sys.argv):
        os.environ["K8SSMASH_RS"] = sys.argv[_i + 1]
    elif _arg == "--lowres":
        os.environ["K8SSMASH_RS"] = "1"

try:
    from k8ssmash.main import main
except ModuleNotFoundError as exc:  # most often a Python package missing from the venv the service runs in
    sys.exit(f"k8ssmash: missing Python package '{exc.name}'. Re-run deploy/setup-pi.sh, or `pip install -e .` in this "
             f"environment (the game needs pygame-ce and numpy).")

main()
