# Using TV Boxsets with other skins

The *Estuary (Boxsets)* skin copy is only needed for Estuary, because Estuary cannot have extra
main-menu items added from its settings. Many other skins have their own menu or widget editors
and can point straight at the add-on, with no skin copy at all.

I have only tested the add-on with Estuary on Kodi 22 RC1. Menu names differ between skins and
versions, so treat the steps below as a guide and look for the equivalent options in your skin.

## The addresses to use

| What you want | Address |
|---|---|
| A main-menu item or shortcut that opens your boxsets | `plugin://plugin.video.tvboxsets/` |
| A widget row of your boxsets | `plugin://plugin.video.tvboxsets/?action=widget` |
| A widget row of the shows to carry on with (one per boxset you are part-way through) | `plugin://plugin.video.tvboxsets/?action=widget&filter=in_progress` |

### Keeping a widget up to date

Rows fed by an add-on only reload when their address changes. The add-on changes a Home-window
property called `tvboxsets_reload` whenever your boxsets or watched progress change, so if your
skin lets you edit the widget address, append this to it and the row will refresh by itself:

`&reload=$INFO[Window(Home).Property(tvboxsets_reload)]`

For example: `plugin://plugin.video.tvboxsets/?action=widget&reload=$INFO[Window(Home).Property(tvboxsets_reload)]`.
Some skins add their own reload value; if yours does, you don't need this.

## Typical steps

1. In your skin's settings, find where you add **main menu items** or **widgets** (look for
   words like "menu", "widgets", "customise home" or "skin shortcuts").
2. Choose to add an **add-on** or **plugin path** and paste one of the addresses above (or pick
   TV Boxsets from the list of video add-ons if your skin offers one).
3. For a widget, choose a poster or list style, as for any other widget.

## Notes

- The widget address lists boxsets only, without the "create" and "tools" rows.
- Boxsets can also be written into Kodi as tags (**Tools > Write boxsets to Kodi tags**), so
  skins that filter by tag can use them without any add-on address.
- Please report what works and what doesn't on your skin, including the skin name and version.
