"""Stand-in for `xbmcgui` with scriptable dialogs (answers are queued in Dialog.Q)."""
NOTIFICATION_INFO = 0
INPUT_ALPHANUM = 0


class _Tag:
    def __init__(self):
        self.d = {}

    def __getattr__(self, name):
        if name.startswith("set"):
            return lambda *a, **k: self.d.__setitem__(name[3:], a[0] if a else None)
        if name.startswith("add") and name.endswith("Stream"):
            return lambda detail: self.d.setdefault(name[3:] + "s", []).append(detail)
        raise AttributeError(name)


class ListItem:
    def __init__(self, label="", label2=""):
        self.label, self.label2 = label, label2
        self.art, self.props, self.tag, self.ctx = {}, {}, _Tag(), []

    def setLabel2(self, label2):
        self.label2 = label2

    def setArt(self, art):
        self.art.update(art)

    def getVideoInfoTag(self):
        return self.tag

    def addContextMenuItems(self, items):
        self.ctx = items

    def setProperty(self, key, value):
        self.props[key] = value


class Window:
    """Home-window properties (id 10000) shared by everything in the test run."""
    _props = {}

    def __init__(self, window_id=10000):
        self.id = window_id

    def setProperty(self, key, value):
        Window._props[key] = value

    def getProperty(self, key):
        return Window._props.get(key, "")


class DialogProgress:
    def create(self, heading, message=""):
        pass

    def update(self, percent, message=""):
        pass

    def iscanceled(self):
        return False

    def close(self):
        pass


class Dialog:
    Q = {}    # method name -> list of answers, consumed in order
    LOG = []

    def _next(self, method, default):
        queue = Dialog.Q.get(method, [])
        value = queue.pop(0) if queue else default
        Dialog.LOG.append((method, value))
        return value

    def select(self, heading, options, preselect=-1, **kwargs):
        return self._next("select", -1)

    def multiselect(self, heading, options, autoclose=0, preselect=None, useDetails=False):
        Dialog.LAST_MULTI = {"heading": heading, "preselect": list(preselect or []),
                             "options": [getattr(o, "label", o) for o in options]}
        return self._next("multiselect", None)

    def input(self, heading, defaultt="", type=0):
        return self._next("input", "")

    def numeric(self, kind, heading, defaultt=""):
        return self._next("numeric", "")

    def yesno(self, heading, message):
        return self._next("yesno", False)

    def ok(self, heading, message):
        Dialog.LOG.append(("ok", message))
        print("  OK-DIALOG:", message.replace("\n", " | "))
        return True

    def textviewer(self, heading, text):
        Dialog.LOG.append(("textviewer", text))

    def browseSingle(self, *args, **kwargs):
        return self._next("browseSingle", "")

    def notification(self, heading, message, *args):
        print("  NOTIFY:", message)
