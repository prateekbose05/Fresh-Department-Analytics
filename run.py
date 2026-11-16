"""Start the dashboard:  python3 run.py

Same as `streamlit run app.py`, with one setting applied first.

Streamlit sends chart and table data to the browser through pyarrow. On macOS
(Python 3.13, pyarrow 25.0.0) pyarrow's default memory allocator crashed the
server with a segmentation fault whenever a filter change redrew the page. The
system allocator does not crash, and it has to be chosen before pyarrow is
loaded, which is why it is set here and not inside app.py.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from streamlit.web import cli  # noqa: E402  (must come after the setting above)

if __name__ == "__main__":
    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app), *sys.argv[1:]]
    sys.exit(cli.main())
