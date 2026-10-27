> **This project's own repository is published automatically.** Pushing a `v...` tag runs the Release
> workflow, which builds the repository and publishes it on GitHub Pages (the `gh-pages` branch) at
> `https://<owner>.github.io/<repo>/`. One-time setup: repository **Settings > Pages > Source: Deploy from a
> branch > `gh-pages` / `(root)`** (the branch appears after the first release), and **Settings > Actions >
> General > Workflow permissions: Read and write**. The rest of this page is for hosting a repository
> yourself on another server.

# Hosting updates without GitHub

You only need somewhere that serves plain files over the web, such as your own website's
hosting. No accounts with any code-hosting service are required.

## What you end up with

A folder (for example `kodi`) on your website containing:

```
addons.xml
addons.xml.md5
repository.tvboxsets-1.0.0.zip      <- testers install this ONE file by hand
zips/...                            <- Kodi downloads add-on updates from here
```

Testers install `repository.tvboxsets-1.0.0.zip` once (Settings > Add-ons > Install from zip
file). After that, whenever you upload a newer version, Kodi offers it as a normal add-on
update.

## Steps

1. **Pick the web address** the folder will live at, for example
   `https://your-website.example/kodi/`. It must be reachable by anyone who should get
   the add-on.
2. **Build the folder.**
   - If you can run Python: `python3 tools/make_repo.py --base-url https://your-website.example/kodi/`
     (the folder appears in `dist/repo`).
   - If not, give the address to whoever maintains the add-on and ask for a ready-made
     folder: nothing else is needed from you.
3. **Upload** everything inside that folder to the address from step 1, keeping the same
   layout (use your host's file manager or FTP).
4. **Check** by opening `https://your-website.example/kodi/addons.xml` in a browser. You should
   see text starting with `<addons>`.
5. **Share** `repository.tvboxsets-1.0.0.zip` with testers (a download link on your page is
   fine).

## Releasing a new version later

Raise the `version` in `plugin.video.tvboxsets/addon.xml`, build the folder again with the
**same** web address, and upload it over the old one. Do not change `--repo-version` unless the
web address changes.

## Test it with Kodi, not just a browser

A browser can open `addons.xml` even when Kodi cannot. Some free hosts show visitors a
"checking your browser" page (it needs JavaScript) before serving any file, and Kodi cannot
pass that check; it would receive the check page instead of the file.

To test properly: install `repository.tvboxsets-1.0.0.zip` in Kodi, then open
**Add-ons > Install from repository > TV Boxsets Repository**. If it lists *TV Boxsets*,
hosting works. If it says it could not connect or retrieve the repository, the host is
blocking Kodi: either use a host without that check, or rebuild the folder for a different
web address with `tools/make_repo.py --base-url ...`.

## If your host blocks Kodi: a drag-and-drop host

Services such as Netlify Drop let you drag a folder (or zip) onto a web page and get a link,
with no Git or command line. Because the web address is written into the repository add-on,
the order is: (1) drop a placeholder page to get your address, (2) build the repository for
that address, (3) drop the repository folder onto the same site. Check the host's current
rules (for example, a site made without signing in may be deleted after a short time, so
create a free account to keep it).

## Notes

- `https://` is better than `http://` if your host supports it.
- Keep the web address stable: it is written into the repository add-on that testers install.
- Each time you upload, `addons.xml` and `addons.xml.md5` must be uploaded together.
