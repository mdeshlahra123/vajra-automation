"""Shared ledger of when each photo / clip was last used in a reel, post or story (owner, 30 Oct:
"use the same photo/video only after a long time"). File: social/media-usage.json {name: "YYYY-MM-DD"}.
  fresh(names, days)  -> names not used in the last `days` days, least-recently-used first
  pick(names, days)   -> best name to use now (fresh if possible, else the least recently used)
  mark(*names)        -> record use today
"""
import datetime, json, os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media-usage.json")
COOLDOWN = 21  # days before the same photo/clip may appear again


def _load():
    try:
        return json.load(open(PATH, encoding="utf-8"))
    except Exception:
        return {}


def _today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).date()


def age(name, u=None):
    u = u if u is not None else _load()
    d = u.get(name)
    return 9999 if not d else (_today() - datetime.date.fromisoformat(d)).days


def fresh(names, days=COOLDOWN):
    u = _load()
    return sorted([n for n in names if age(n, u) >= days], key=lambda n: -age(n, u))


def pick(names, days=COOLDOWN, avoid=()):
    u = _load()
    pool = [n for n in names if n not in avoid] or list(names)
    f = [n for n in pool if age(n, u) >= days]
    return max(f or pool, key=lambda n: age(n, u))


def mark(*names):
    u = _load(); t = _today().isoformat()
    for n in names:
        if n:
            u[n] = t
    json.dump(u, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
