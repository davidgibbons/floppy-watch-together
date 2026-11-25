#!/usr/bin/env python3
"""Copy plays of titles on a Floppy list to another Floppy user."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

EXTERNAL_ID_PREFIX = "fwt:"
PAGE = 200


class Floppy:
    def __init__(self, url, token):
        self.url = url.rstrip("/") + "/api/v1/"
        self.token = token

    def request(self, method, path, params=None, body=None):
        url = self.url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.load(resp)

    def paged(self, path, params=None):
        params = dict(params or {}, limit=PAGE, offset=0)
        while True:
            _, page = self.request("GET", path, params)
            yield from page["results"]
            if not page["pagination"].get("next"):
                return
            params["offset"] += PAGE


def load_links(env):
    """Return {name: (list, token)} from LINK_<NAME>_LIST / LINK_<NAME>_TOKEN."""
    links = {}
    for key, value in env.items():
        m = re.fullmatch(r"LINK_(\w+?)_(LIST|TOKEN)", key)
        if m:
            links.setdefault(m[1], {})[m[2]] = value
    for name, link in links.items():
        if set(link) != {"LIST", "TOKEN"}:
            sys.exit(f"LINK_{name}_LIST and LINK_{name}_TOKEN must both be set")
    return {name: (link["LIST"], link["TOKEN"]) for name, link in links.items()}


def find_list(lists, wanted):
    """Match a list by id when `wanted` is numeric, else by name (case-insensitive)."""
    for lst in lists:
        if str(lst["id"]) == wanted or lst["name"].casefold() == wanted.casefold():
            return lst
    return None


def title_key(item):
    """Episodes and seasons carry their show's media_id, so one key covers a whole show."""
    kind = "movie" if item["media_type"] == "movie" else "tv"
    return (kind, item["source"], str(item["media_id"]))


def watch_call(entry):
    """Return (path, body) that records `entry` as a play, or None if it can't be copied."""
    item = entry["item"]
    if not entry.get("end_date") or item["media_type"] not in ("episode", "movie"):
        return None
    body = {
        "end_date": entry["end_date"],
        "external_id": EXTERNAL_ID_PREFIX + str(entry["entry_key"]),
    }
    src = urllib.parse.quote(item["source"])
    mid = urllib.parse.quote(str(item["media_id"]))
    if item["media_type"] == "movie":
        return f"media/movie/{src}/{mid}/watch/", body
    return (
        f"media/tv/{src}/{mid}/{item['season_number']}"
        f"/episodes/{item['episode_number']}/watch/",
        body,
    )


def run_once(env):
    url = env["FLOPPY_URL"]
    me = Floppy(url, env["SOURCE_TOKEN"])
    dry_run = env.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    since = date.today() - timedelta(days=int(env.get("LOOKBACK_DAYS", "7")))

    history = list(me.paged("history/", {"flat": 1, "start_date": since.isoformat()}))
    lists = list(me.paged("lists/"))
    print(f"{len(history)} plays since {since}")

    failed = False
    for name, (wanted, token) in load_links(env).items():
        lst = find_list(lists, wanted)
        if lst is None:
            print(f"[{name}] no list named or numbered {wanted!r}")
            failed = True
            continue
        titles = {title_key(i["item"]) for i in me.paged(f"lists/{lst['id']}/items/")}
        them = Floppy(url, token)
        added = skipped = 0
        for entry in history:
            call = watch_call(entry)
            if call is None or title_key(entry["item"]) not in titles:
                continue
            label = f"{entry.get('show', {}).get('title') or entry['title']} {entry.get('episode_code') or ''}".strip()
            if dry_run:
                print(f"[{name}] would add {label} @ {entry['end_date']}")
                continue
            path, body = call
            try:
                status, _ = them.request("POST", path, body=body)
            except urllib.error.HTTPError as e:
                print(f"[{name}] {label}: HTTP {e.code} {e.read()[:200]!r}")
                failed = True
                continue
            if status == 201:
                added += 1
                print(f"[{name}] added {label} @ {entry['end_date']}")
            else:
                skipped += 1
        print(f"[{name}] {lst['name']}: {len(titles)} titles, {added} added, {skipped} already there")
    return not failed


def main():
    interval = int(os.environ.get("INTERVAL_SECONDS", "0"))
    while True:
        ok = run_once(os.environ)
        if not interval:
            sys.exit(0 if ok else 1)
        time.sleep(interval)


if __name__ == "__main__":
    main()
