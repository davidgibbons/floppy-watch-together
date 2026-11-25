# floppy-watch-together

Copies your [Floppy](https://github.com/dannyvfilms/floppy) plays to someone
else's Floppy account, for the titles on a list you choose. Put the shows you
watch with Jess on a "Watch With Jess" list; every episode you mark watched
there is added to Jess's history with the same date.

It is a stopgap until Floppy ships
["Watched with"](https://github.com/dannyvfilms/floppy/issues/962).

## How it works

Each run reads your history for the last `LOOKBACK_DAYS` days. For every
episode or movie whose show or movie is on a linked list, it records a play on
the other account with your play's date. Each copied play carries an
`external_id` of `fwt:<your history entry id>`, so a later run never adds the
same play twice.

It only adds plays. Unwatching or deleting a play on your account does not
touch the other account.

## Tokens

Create an API token in Floppy for each account:

| Token | Account | Scopes |
| --- | --- | --- |
| `SOURCE_TOKEN` | yours (the list owner) | `lists:read`, `watchlist:read` |
| `LINK_<NAME>_TOKEN` | each person you link | `watchlist:write` |

## Configuration

All settings are environment variables. See `.env.example`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `FLOPPY_URL` | required | Base URL of your Floppy instance |
| `SOURCE_TOKEN` | required | Your token |
| `LINK_<NAME>_LIST` | | List name (case-insensitive) or numeric id |
| `LINK_<NAME>_TOKEN` | | Token of the person to copy plays to |
| `LOOKBACK_DAYS` | `7` | How far back each run reads your history |
| `DRY_RUN` | off | `true` prints what would be added and writes nothing |
| `INTERVAL_SECONDS` | `0` | `0` runs once and exits; otherwise repeats on this interval |

Add one `LINK_<NAME>_LIST` / `LINK_<NAME>_TOKEN` pair per person, for example
`LINK_JESS_*` and `LINK_KATI_*`.

To copy plays from before you started, run once with a larger `LOOKBACK_DAYS`.

## Running

Locally (Python 3.10+, no dependencies):

```sh
cp .env.example .env    # fill in tokens; DRY_RUN=true to start
set -a; . ./.env; set +a
python3 floppy_watch_together.py
```

With Docker Compose, which repeats hourly:

```sh
cp docker-compose.example.yaml docker-compose.yaml
docker compose up -d
```

As a Kubernetes CronJob, run the image `ghcr.io/davidgibbons/floppy-watch-together`
with the variables above and leave `INTERVAL_SECONDS` unset. Keep
`LOOKBACK_DAYS` longer than the schedule so a missed run is caught up.

The exit code is `1` when a list is not found or a write fails.

## Limitations

- If the other person also logs the same play (by hand or from their own
  media-server webhook), they get two plays.
- Only episodes and movies are copied. Books, games and music are skipped.
- Changing a title's list membership does not backfill; only plays inside the
  lookback window are copied.

## Development

```sh
python3 -m unittest
```
