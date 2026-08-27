"""Keep macOS version detection reliable in frozen Python applications.

Some macOS/Python combinations return an empty release string from
``platform.mac_ver()`` inside a PyInstaller app.  darkdetect 0.8.0 converts
that release to ``int`` while CustomTkinter is imported, which otherwise
crashes ACAN Studio before its first window appears.
"""

import platform
import subprocess
import sys


_original_mac_ver = platform.mac_ver


def _safe_mac_ver(release="", versioninfo=("", "", ""), machine=""):
    detected = _original_mac_ver(release, versioninfo, machine)
    if sys.platform != "darwin" or detected[0]:
        return detected

    try:
        system_release = subprocess.run(
            ["/usr/bin/sw_vers", "-productVersion"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except Exception:
        system_release = ""

    # ACAN Studio targets macOS 11 or newer.  The fallback only prevents an
    # import-time crash if both Python and sw_vers fail to report a version.
    return (system_release or "11.0", detected[1], detected[2])


platform.mac_ver = _safe_mac_ver
