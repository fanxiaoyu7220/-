"""Run PyInstaller while preserving a relocated python.org framework.

PyInstaller already forwards DYLD_LIBRARY_PATH through macOS's ``arch``
launcher, but not DYLD_FRAMEWORK_PATH.  The latter is needed only by ACAN's
isolated, locally extracted Universal2 build runtime.  It is not needed by the
finished app.
"""

import os

import PyInstaller.compat as compat


_original_wrap_python = compat.__dict__["__wrap_python"]


def _wrap_python_with_framework_path(args, kwargs):
    command, options = _original_wrap_python(args, kwargs)
    framework_path = os.environ.get("DYLD_FRAMEWORK_PATH", "").strip()
    if framework_path and command and os.path.basename(command[0]) == "arch":
        command[1:1] = ["-e", f"DYLD_FRAMEWORK_PATH={framework_path}"]
    return command, options


compat.__dict__["__wrap_python"] = _wrap_python_with_framework_path

from PyInstaller.__main__ import run


if __name__ == "__main__":
    run()
