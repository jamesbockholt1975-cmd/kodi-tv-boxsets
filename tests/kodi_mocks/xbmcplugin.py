"""Stand-in for `xbmcplugin`: records the items a view adds."""
ITEMS = []
SORT_METHOD_NONE = 0


def setContent(handle, content):
    pass


def addDirectoryItem(handle, url, listitem, isFolder=False):
    ITEMS.append((listitem, url, isFolder))
    return True


def addSortMethod(handle, method):
    pass


def endOfDirectory(handle, succeeded=True):
    pass


def setResolvedUrl(handle, succeeded, listitem):
    pass
