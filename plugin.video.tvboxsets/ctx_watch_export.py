# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Right-click script (see ctxutil.py): save this watch order to a file."""

import ctxutil

if __name__ == "__main__":
    ctxutil.run_plugin(action="watch_export", bid=ctxutil.current_bid())
