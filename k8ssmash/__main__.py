import os
import sys

# The render scale decides every surface size at import time, so it is read before the game modules load.
for _i, _arg in enumerate(sys.argv):
    if _arg == "--render-scale" and _i + 1 < len(sys.argv):
        os.environ["K8SSMASH_RS"] = sys.argv[_i + 1]
    elif _arg == "--lowres":
        os.environ["K8SSMASH_RS"] = "1"

from k8ssmash.main import main  # noqa: E402

main()
