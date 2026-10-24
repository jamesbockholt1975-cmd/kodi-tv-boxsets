"""Minimal stand-in for Kodi's `xbmc` module, just enough for the test-suite."""
import json

LOGERROR = 0
LOGINFO = 1
LOGS = []
SKIN = "skin.estuary"
BUILTINS = []
INFO = {}
ENABLED = set()
RPC_LOG = []
LIB = []        # TV shows returned by VideoLibrary.GetTVShows
MOVIES = []     # movies returned by VideoLibrary.GetMovies
EPISODES = {}   # tvshowid -> episodes returned by VideoLibrary.GetEpisodes
TAGS = {}       # {"tvshow": [labels], "movie": [labels]} returned by VideoLibrary.GetTags


class Monitor:
    """Minimal Monitor: the service loop exits immediately in tests."""

    def abortRequested(self):
        return True

    def waitForAbort(self, timeout=0):
        return True


def getSkinDir():
    return SKIN


def getInfoLabel(key):
    return INFO.get(key, "")


def executebuiltin(command):
    BUILTINS.append(command)


def getCondVisibility(condition):
    return "skin.estuary.boxsets" in ENABLED


def sleep(ms):
    pass


def log(message, level=0):
    LOGS.append((level, message))
    print("LOG:", message)


def _by_tag(items, flt):
    if flt and flt.get("field") == "tag":
        return [i for i in items if flt["value"] in i.get("tag", [])]
    return items


def executeJSONRPC(request):
    q = json.loads(request)
    method, params = q["method"], q.get("params", {})
    RPC_LOG.append((method, params))
    if method == "VideoLibrary.GetTVShows":
        return json.dumps({"result": {"tvshows": _by_tag(LIB, params.get("filter"))}})
    if method == "VideoLibrary.GetMovies":
        return json.dumps({"result": {"movies": _by_tag(MOVIES, params.get("filter"))}})
    if method == "VideoLibrary.GetTVShowDetails":
        show = [s for s in LIB if s["tvshowid"] == params["tvshowid"]][0]
        return json.dumps({"result": {"tvshowdetails": show}})
    if method == "VideoLibrary.GetMovieDetails":
        movie = [m for m in MOVIES if m["movieid"] == params["movieid"]][0]
        return json.dumps({"result": {"moviedetails": movie}})
    if method == "VideoLibrary.GetEpisodes":
        eps = EPISODES.get(params["tvshowid"], [])
        if params.get("filter"):  # unwatched, real seasons only
            eps = [e for e in eps if e.get("playcount", 0) == 0 and e.get("season", 1) > 0]
        return json.dumps({"result": {"episodes": eps}})
    if method == "VideoLibrary.GetTags":
        return json.dumps({"result": {"tags": [
            {"tagid": i, "label": l} for i, l in enumerate(TAGS.get(params["type"], []))]}})
    if method == "VideoLibrary.SetTVShowDetails":
        for s in LIB:
            if s["tvshowid"] == params["tvshowid"] and "tag" in params:
                s["tag"] = list(params["tag"])
    if method == "VideoLibrary.SetMovieDetails":
        for m in MOVIES:
            if m["movieid"] == params["movieid"]:
                if "tag" in params:
                    m["tag"] = list(params["tag"])
                if "playcount" in params:
                    m["playcount"] = params["playcount"]
    if method == "VideoLibrary.SetEpisodeDetails":
        for eps in EPISODES.values():
            for e in eps:
                if e["episodeid"] == params["episodeid"] and "playcount" in params:
                    e["playcount"] = params["playcount"]
    if method == "Addons.SetAddonEnabled":
        ENABLED.add(params["addonid"])
    return json.dumps({"result": "OK"})
