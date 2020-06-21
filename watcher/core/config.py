import json
import random
import datetime
from watcher import core
import collections
from . import localization
from .helpers import Comparisons

""" Config
Config is a simple json object that is loaded into core.CONFIG as a dict

All sections and subsections must be capitalized. All keys must be lower-case.
No spaces, underscores, or hyphens.
Be terse but descriptive.
"""

base_file = "core/base_config.cfg"


def default_profile():
    return [
        k for k, v in core.CONFIG["Quality"]["Profiles"].items() if v.get("default")
    ][0]


def new_config():
    """ Copies base_file to config directory.

    Automatically assigns random values to searchtimehr, searchtimemin,
        installupdatehr, installupdatemin, and apikey.

    Config template is stored as core/base_config.cfg

    When adding keys to the base config:
        Keys will have no spaces, hypens, underscores or other substitutions
            for a space. Simply crush everything into one word.
        Keys that access another dictionary should be capitalized. This can
            be done in the way that makes most sense in context, but should
            try to mimic camel case.
        Keys that access a non-dictionary value should be lowercase.

    Returns dict of newly created config
    """

    with open(base_file, "r") as f:
        config = json.load(f)

    config["Search"]["searchtimehr"] = random.randint(0, 23)
    config["Search"]["searchtimemin"] = random.randint(0, 59)

    config["Server"]["installupdatehr"] = random.randint(0, 23)
    config["Server"]["installupdatemin"] = random.randint(0, 59)

    config["Search"]["popularmovieshour"] = random.randint(0, 23)
    config["Search"]["popularmoviesmin"] = random.randint(0, 59)

    apikey = "%06x" % random.randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
    config["Server"]["apikey"] = apikey

    config["Quality"]["Profiles"]["Default"] = base_profile

    with open(core.CONF_FILE, "w") as f:
        json.dump(config, f, indent=4, sort_keys=True)
    return config


def write(data):
    """ Writes a dict to the config file.
    data (dict): Config section with nested dict of keys and values:

    {'Section': {'key': 'val', 'key2': 'val2'}, 'Section2': {'key': 'val'}}

    MUST contain fully populated sections or data will be lost.

    Only modifies supplied section.

    After updating config file, copies to core.CONFIG via load()

    Does not return.
    """

    diff = Comparisons.compare_dict(data, core.CONFIG)

    core.CONFIG.update(data)

    with open(core.CONF_FILE, "w") as f:
        json.dump(core.CONFIG, f, indent=4, sort_keys=True)

    load(config=core.CONFIG)

    if diff:
        restart_scheduler(diff)
        l = diff.get("Server", {}).get("language")
        if l:
            localization.install(l)

    return


def merge_new_options():
    """ Merges new options in base_config with config

    Opens base_config and config, then saves them merged with config taking priority.

    Does not return
    """

    new_config = {}

    with open(base_file, "r") as f:
        base_config = json.load(f)
    with open(core.CONF_FILE, "r") as f:
        config = json.load(f)

    new_config = _merge(base_config, config)

    # Convert imdb str to list
    if type(new_config["Search"]["Watchlists"]["imdbrss"]) == str:
        new_config["Search"]["Watchlists"]["imdbrss"] = new_config["Search"][
            "Watchlists"
        ]["imdbrss"].split(",")

    # Convert from predb-only verifying to multiple choice
    if new_config["Search"].get("predbcheck") is True:
        new_config["Search"]["verifyreleases"] = "predb"
        del new_config["Search"]["predbcheck"]

    # Convert from hardlink option to multiple choice
    if new_config["Postprocessing"].get("createhardlink") is True:
        new_config["Postprocessing"]["movermethod"] = "hardlink"
        del new_config["Postprocessing"]["createhardlink"]

    # Add Default profile if there are none
    if len(new_config["Quality"]["Profiles"]) == 0:
        new_config["Quality"]["Profiles"]["Default"] = base_profile

    # Set first profile to 'default': True if none are set
    d = [prof.get("default") for prof in new_config["Quality"]["Profiles"].values()]
    if not any(d):
        target = (
            "Default"
            if new_config["Quality"]["Profiles"].get("Default")
            else list(new_config["Quality"]["Profiles"].keys())[0]
        )
        print(
            "Default Quality Profile not specified, setting *{}* to Default.".format(
                target
            )
        )
        new_config["Quality"]["Profiles"][target]["default"] = True

    with open(core.CONF_FILE, "w") as f:
        json.dump(new_config, f, indent=4, sort_keys=True)

    return


def _merge(d, u):
    """ Deep merge dictionaries
    d (dict): base dict to merge into
    u (dict): dict to update from

    If any k:v pair in u is not in d, adds k:v pair.

    Will not overwrite any values in d, nor will it remove
        any k:v pairs in d.

    Returns dict
    """
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = _merge(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def dump(config=core.CONFIG):
    """ Writes config to file
    config (dict): Config contenst to write to disk  <optional - default core.CONFIG>

    Opposite of load. Writes config to disk

    Returns bool
    """
    try:
        with open(core.CONF_FILE, "w") as f:
            json.dump(config, f, indent=4, sort_keys=True)
    except Exception as e:
        return False

    return True


def load(config=None):
    """ Stores entire config as dict to core.CONFIG
    config (dict): Config file contents <optional>

    If 'config' is not supplied, reads config from disk. If calling load() from
        a method in this class pass the saved config so we don't have to read from
        a file we just wrote to.

    Sanitizes input when neccesary.

    Opposite of dump -- loads config into memory.

    Does not return
    """

    if not config:
        with open(core.CONF_FILE, "r") as f:
            config = json.load(f)

    repl = config["Postprocessing"]["replaceillegal"]
    if repl in ('"', "*", "?", "<", ">", "|", ":"):
        config["Postprocessing"]["replaceillegal"] = ""

    core.CONFIG = config

    return


def restart_scheduler(diff):
    """ Restarts and scheduled tasks in diff
    diff (dict): modified keys in config file

    Reads diff and determines which tasks need to be restart_scheduler

    Does not return
    """

    now = datetime.datetime.today()

    if "Server" in diff:
        d = diff["Server"].keys()

        if any(i in d for i in ("checkupdates", "checkupdatefrequency")):
            hr = now.hour + core.CONFIG["Server"]["checkupdatefrequency"]
            min = now.minute
            interval = core.CONFIG["Server"]["checkupdatefrequency"] * 3600
            auto_start = core.CONFIG["Server"]["checkupdates"]
            core.scheduler_plugin.task_list["Update Checker"].reload(
                hr, min, interval, auto_start=auto_start
            )

    if "Search" in diff:
        d = diff["Search"].keys()
        if "rsssyncfrequency" in d:
            hr = now.hour
            min = now.minute + core.CONFIG["Search"]["rsssyncfrequency"]
            interval = core.CONFIG["Search"]["rsssyncfrequency"] * 60
            auto_start = True
            core.scheduler_plugin.task_list["Movie Search"].reload(
                hr, min, interval, auto_start=auto_start
            )

        if "Watchlists" in d:
            d = diff["Search"]["Watchlists"].keys()
            if any(i in d for i in ("imdbfrequency", "imdbsync")):
                hr = now.hour
                min = now.minute + core.CONFIG["Search"]["Watchlists"]["imdbfrequency"]
                interval = core.CONFIG["Search"]["Watchlists"]["imdbfrequency"] * 60
                auto_start = core.CONFIG["Search"]["Watchlists"]["imdbsync"]
                core.scheduler_plugin.task_list["IMDB Sync"].reload(
                    hr, min, interval, auto_start=auto_start
                )

            if any(
                i in d
                for i in ("popularmoviessync", "popularmovieshour", "popularmoviesmin")
            ):
                hr = core.CONFIG["Search"]["Watchlists"]["popularmovieshour"]
                min = core.CONFIG["Search"]["Watchlists"]["popularmoviesmin"]
                interval = 24 * 3600
                auto_start = core.CONFIG["Search"]["Watchlists"]["popularmoviessync"]
                core.scheduler_plugin.task_list["PopularMovies Sync"].reload(
                    hr, min, interval, auto_start=auto_start
                )

            if any(i in d for i in ("traktsync", "traktfrequency")):
                hr = now.hour
                min = now.minute + core.CONFIG["Search"]["Watchlists"]["traktfrequency"]
                interval = core.CONFIG["Search"]["Watchlists"]["traktfrequency"] * 60
                auto_start = core.CONFIG["Search"]["Watchlists"]["traktsync"]
                core.scheduler_plugin.task_list["Trakt Sync"].reload(
                    hr, min, interval, auto_start=auto_start
                )

    if "Postprocessing" in diff:
        d = diff["Postprocessing"].get("Scanner", {})
        if any(i in d for i in ("interval", "enabled")):
            hr = now.hour
            min = now.minute + core.CONFIG["Postprocessing"]["Scanner"]["interval"]
            interval = core.CONFIG["Postprocessing"]["Scanner"]["interval"] * 60
            auto_start = core.CONFIG["Postprocessing"]["Scanner"]["enabled"]
            core.scheduler_plugin.task_list["PostProcessing Scan"].reload(
                hr, min, interval, auto_start=auto_start
            )

    if "System" in diff:
        d = diff["System"]["FileManagement"].keys()
        if any(
            i in d for i in ("scanmissingfiles", "scanmissinghour", "scanmissingmin")
        ):
            hr = core.CONFIG["System"]["FileManagement"]["scanmissinghour"]
            min = core.CONFIG["System"]["FileManagement"]["scanmissingmin"]
            interval = 24 * 3600
            auto_start = core.CONFIG["System"]["FileManagement"]["scanmissingfiles"]
            core.scheduler_plugin.task_list["Missing Files Scan"].reload(
                hr, min, interval, auto_start=auto_start
            )

    if "Downloader" in diff and "Torrent" in diff["Downloader"]:
        auto_start = False
        client = None
        if core.CONFIG["Downloader"]["Sources"]["torrentenabled"]:
            for name, config in core.CONFIG["Downloader"]["Torrent"].items():
                ignore_remove_torrents = name == "DelugeRPC" or name == "DelugeWeb"
                if config["enabled"] and (
                    not ignore_remove_torrents
                    and config.get("removetorrents")
                    or config.get("removestalledfor")
                ):
                    auto_start = True
                    client = name
                    break
        if auto_start:
            d = diff["Downloader"]["Torrent"].get(client, {}).keys()
            setting_keys = ["enabled", "removestalledfor"]
            if client != "DelugeRPC" and client != "DelugeWeb":
                setting_keys.append("removetorrents")
            if any(i in d for i in setting_keys):
                hr = (now.hour + 1) % 24
                min = now.minute
                core.scheduler_plugin.task_list["Torrents Status Check"].reload(
                    hr, min, 3600, auto_start=True
                )
        else:
            core.scheduler_plugin.task_list["Torrents Status Check"].reload(
                0, 0, 3600, auto_start=False
            )


"""
base_profile is used as the template quality profile if none is present.
"""

base_profile = json.loads(
    """
{"Sources": {
        "BluRay-1080P": [
            true,
            1
        ],
        "BluRay-4K": [
            false,
            0
        ],
        "BluRay-720P": [
            true,
            2
        ],
        "CAM-SD": [
            false,
            13
        ],
        "DVD-SD": [
            false,
            9
        ],
        "Screener-1080P": [
            false,
            10
        ],
        "Screener-720P": [
            false,
            11
        ],
        "Telesync-SD": [
            false,
            12
        ],
        "WebDL-1080P": [
            true,
            4
        ],
        "WebDL-4K": [
            false,
            3
        ],
        "WebDL-720P": [
            true,
            5
        ],
        "WebRip-1080P": [
            true,
            7
        ],
        "WebRip-4K": [
            false,
            6
        ],
        "WebRip-720P": [
            true,
            8
        ],
        "Unknown": [
            false,
            14
        ]

    },
    "ignoredwords": "subs,german,dutch,french,truefrench,danish,swedish,spanish,italian,korean,dubbed,swesub,korsub,dksubs,vain,HC,blurred",
    "preferredwords": "",
    "prefersmaller": false,
    "requiredwords": "",
    "scoretitle": true,
    "default": true
}
"""
)
