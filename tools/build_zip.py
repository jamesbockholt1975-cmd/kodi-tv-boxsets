#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the installable add-on zip:  python3 tools/build_zip.py

Writes dist/plugin.video.tvboxsets-<version>.zip. The version comes from addon.xml.
Files are added in sorted order with fixed timestamps, so the same source always
produces the same zip.
"""
import os
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADDON_ID = "plugin.video.tvboxsets"


def read_version(addon_dir):
    with open(os.path.join(addon_dir, "addon.xml"), encoding="utf-8") as f:
        return re.search(r'<addon\b[^>]*?\sversion="([^"]+)"', f.read()).group(1)


def check_xml(src_dir):
    """Every .xml file in the add-on must be well-formed; Kodi would silently ignore a broken one."""
    for folder, _, names in os.walk(src_dir):
        for name in names:
            if name.endswith(".xml"):
                path = os.path.join(folder, name)
                try:
                    ET.parse(path)
                except ET.ParseError as exc:
                    raise SystemExit("Not building: {} is not valid XML ({})".format(
                        os.path.relpath(path, src_dir), exc))


def build_zip(src_dir, out_dir):
    """Zip the add-on folder `src_dir` into `out_dir`. Returns (zip_path, version, files)."""
    check_xml(src_dir)
    addon_id = os.path.basename(os.path.abspath(src_dir))
    version = read_version(src_dir)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "{}-{}.zip".format(addon_id, version))

    files = []
    for folder, dirs, names in os.walk(src_dir):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            if not name.endswith(".pyc"):
                files.append(os.path.join(folder, name))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            arc = os.path.join(addon_id, os.path.relpath(path, src_dir)).replace(os.sep, "/")
            info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as f:
                z.writestr(info, f.read())
    return out, version, files


def main():
    out, version, files = build_zip(os.path.join(ROOT, ADDON_ID), os.path.join(ROOT, "dist"))
    print("Built", out)
    for path in files:
        print("  ", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
