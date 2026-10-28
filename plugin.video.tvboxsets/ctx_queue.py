# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Right-click script (see ctxutil.py)."""

import ctxutil

if __name__ == "__main__":
    if ctxutil.in_watch_order():
        ctxutil.run_plugin(action="queue", bid=ctxutil.current_bid(), watch=1)
    else:
        ctxutil.run_plugin(action="queue", bid=ctxutil.current_bid())
