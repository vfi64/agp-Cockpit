from pathlib import Path
from agp_cockpit.app_bootstrap import run

def main() -> int:
    return run(Path.cwd())

if __name__ == '__main__':
    raise SystemExit(main())
