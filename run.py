"""
run.py - Convenience launcher for Memory Match.
Delegates directly to main.py.
"""

import sys
import os

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    if here not in sys.path:
        sys.path.insert(0, here)
    import main
    main.main()

