# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Right-click script (see ctxutil.py): take the highlighted entry out of the watch order only."""

import ctxutil

if __name__ == "__main__":
    ctxutil.run_plugin(action="watch_remove", bid=ctxutil.current_bid(), key=ctxutil.current_key())
