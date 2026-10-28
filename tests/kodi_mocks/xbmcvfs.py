"""Stand-in for `xbmcvfs`: maps special:// paths into a throw-away test folder."""
import os

_MAP = (("special://home/", "home/"), ("special://xbmc/", "xbmc/"),
        ("special://profile/", "profile/"), ("special://temp/", "temp/"),
        ("special://logpath/", "log/"))


def translatePath(path):
    root = os.environ["TVB_TEST_ROOT"]
    for prefix, folder in _MAP:
        if path.startswith(prefix):
            return os.path.join(root, folder + path[len(prefix):])
    return path


def mkdirs(path):
    os.makedirs(path, exist_ok=True)
    return True


class File:
    def __init__(self, path, mode="r"):
        self._path = path
        self._f = open(path, mode, encoding="utf-8")

    def write(self, text):
        self._f.write(text)
        return True

    def read(self):
        return self._f.read()

    def readBytes(self):
        self._f.close()
        with open(self._path, "rb") as raw:
            return bytearray(raw.read())

    def close(self):
        self._f.close()
