#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a Kodi repository you can host on any plain web server (no GitHub needed).

    python3 tools/make_repo.py --base-url https://example.com/kodi/

Creates (default folder dist/repo):

    addons.xml, addons.xml.md5            the repository index Kodi reads
    zips/plugin.video.tvboxsets/...       the add-on zip + icon + fanart
    zips/repository.tvboxsets/...         the repository add-on zip + icon
    repository.tvboxsets-<ver>.zip        the file people install ONCE to get updates

Upload the whole folder so that `addons.xml` is reachable at <base-url>addons.xml.
Testers install repository.tvboxsets-<ver>.zip from zip; after that Kodi finds and
installs new versions of TV Boxsets by itself.
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_zip  # noqa: E402

ROOT = build_zip.ROOT
ADDON_ID = build_zip.ADDON_ID
REPO_ID = "repository.tvboxsets"

REPO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<addon id="{id}" name="TV Boxsets Repository" version="{version}" provider-name="Frecklesnoot">
  <requires>
    <import addon="xbmc.addon" version="12.0.0"/>
  </requires>
  <extension point="xbmc.addon.repository" name="TV Boxsets Repository">
    <dir>
      <info compressed="false">{base}addons.xml</info>
      <checksum>{base}addons.xml.md5</checksum>
      <datadir zip="true">{base}zips/</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary lang="en_GB">Updates for the TV Boxsets add-on</summary>
    <description lang="en_GB">Install this once and Kodi will find and install new versions of TV Boxsets for you.</description>
    <platform>all</platform>
    <assets>
      <icon>icon.png</icon>
    </assets>
  </extension>
</addon>
"""


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TV Boxsets: Kodi repository</title></head>
<body style="font-family:sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5">
<h1>TV Boxsets: Kodi repository</h1>
<p>Alpha build. Current version: <b>{version}</b>.</p>
<ol>
<li>Download <a href="{zip}">{zip}</a> (the repository add-on).</li>
<li>In Kodi: <b>Settings &gt; Add-ons &gt; Install from zip file</b> and choose that file.</li>
<li>Then <b>Add-ons &gt; Install from repository &gt; TV Boxsets Repository</b> to install TV Boxsets.
Kodi will offer future updates by itself.</li>
</ol>
{source}<p>This page exists so the folder can be hosted on drag-and-drop hosts; Kodi only uses
<code>addons.xml</code> and the files under <code>zips/</code>.</p>
</body></html>
"""


def strip_declaration(xml_text):
    return re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", xml_text)


def make_repo(base_url, out_dir, repo_version="1.0.0"):
    if not re.match(r"^https?://[^/\s]+", base_url):
        raise SystemExit("--base-url must start with http:// or https://")
    base = base_url if base_url.endswith("/") else base_url + "/"
    shutil.rmtree(out_dir, ignore_errors=True)
    addon_src = os.path.join(ROOT, ADDON_ID)

    with tempfile.TemporaryDirectory() as tmp:
        repo_src = os.path.join(tmp, REPO_ID)
        os.makedirs(repo_src)
        with open(os.path.join(repo_src, "addon.xml"), "w", encoding="utf-8") as f:
            f.write(REPO_XML.format(id=REPO_ID, version=repo_version, base=base))
        shutil.copy(os.path.join(addon_src, "icon.png"), os.path.join(repo_src, "icon.png"))

        addon_dir = os.path.join(out_dir, "zips", ADDON_ID)
        repo_dir = os.path.join(out_dir, "zips", REPO_ID)
        addon_zip, addon_version, _ = build_zip.build_zip(addon_src, addon_dir)
        repo_zip, _, _ = build_zip.build_zip(repo_src, repo_dir)
        for name in ("icon.png", "fanart.jpg"):
            shutil.copy(os.path.join(addon_src, name), addon_dir)
        shutil.copy(os.path.join(repo_src, "icon.png"), repo_dir)
        shutil.copy(repo_zip, out_dir)  # the one file people install by hand

        parts = []
        for src in (addon_src, repo_src):
            with open(os.path.join(src, "addon.xml"), encoding="utf-8") as f:
                parts.append(strip_declaration(f.read()).strip())

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        source = ""
        found = re.search(r"<source>([^<]+)</source>", open(os.path.join(addon_src, "addon.xml"), encoding="utf-8").read())
        if found:
            source = ('<p>Source code, tests and release zips with checksums: '
                      '<a href="{0}">{0}</a></p>\n'.format(found.group(1).strip()))
        f.write(INDEX_HTML.format(zip=os.path.basename(repo_zip), version=addon_version, source=source))

    index = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n{}\n</addons>\n'.format(
        "\n".join(parts))
    with open(os.path.join(out_dir, "addons.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(index)
    with open(os.path.join(out_dir, "addons.xml.md5"), "w", encoding="ascii") as f:
        f.write(hashlib.md5(index.encode("utf-8")).hexdigest())
    return base, addon_version, os.path.basename(repo_zip)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base-url", required=True, help="where the folder will be hosted, e.g. https://example.com/kodi/")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "repo"))
    ap.add_argument("--repo-version", default="1.0.0",
                    help="raise this if you ever change --base-url so Kodi updates the repository add-on")
    args = ap.parse_args()
    base, version, repo_zip = make_repo(args.base_url, args.out, args.repo_version)
    print("Repository built in", args.out)
    print("Upload the contents of that folder to:", base)
    print("Check it works by opening", base + "addons.xml", "in a browser.")
    print("Testers install", repo_zip, "once (Settings > Add-ons > Install from zip file).")
    print("TV Boxsets", version, "is then offered/updated automatically.")
    if base.startswith("http://"):
        print("Note: plain http:// works but https:// is better if your host offers it.")


if __name__ == "__main__":
    main()
