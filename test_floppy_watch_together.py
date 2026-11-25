import io
import json
import unittest
from unittest import mock

from floppy_watch_together import find_list, load_links, run_once, title_key, watch_call

EPISODE = {
    "item": {"media_type": "episode", "source": "tmdb", "media_id": "158756",
             "season_number": 5, "episode_number": 6},
    "title": "Who Are We?", "episode_code": "S05E06",
    "end_date": "2026-11-24T18:29:00Z", "entry_key": "1909",
}


class Tests(unittest.TestCase):
    def test_episode_matches_show_on_list(self):
        show = {"media_type": "tv", "source": "tmdb", "media_id": "158756"}
        self.assertEqual(title_key(EPISODE["item"]), title_key(show))

    def test_movie_does_not_match_tv_with_same_id(self):
        movie = {"media_type": "movie", "source": "tmdb", "media_id": "158756"}
        self.assertNotEqual(title_key(EPISODE["item"]), title_key(movie))

    def test_watch_call(self):
        path, body = watch_call(EPISODE)
        self.assertEqual(path, "media/tv/tmdb/158756/5/episodes/6/watch/")
        self.assertEqual(body, {"end_date": "2026-11-24T18:29:00Z", "external_id": "fwt:1909"})
        self.assertIsNone(watch_call(dict(EPISODE, end_date=None)))

    def test_find_list_by_id_or_name(self):
        lists = [{"id": 1, "name": "Watch With Jess"}]
        self.assertEqual(find_list(lists, "1")["id"], 1)
        self.assertEqual(find_list(lists, "watch with jess")["id"], 1)
        self.assertIsNone(find_list(lists, "nope"))

    def test_run_sends_play_as_json_body(self):
        pages = {
            "history/": [EPISODE],
            "lists/": [{"id": 1, "name": "Watch With Jess"}],
            "lists/1/items/": [{"item": {"media_type": "tv", "source": "tmdb", "media_id": "158756"}}],
        }
        sent = []

        def urlopen(req, timeout):
            path = req.full_url.split("/api/v1/", 1)[1].split("?")[0]
            if req.get_method() == "POST":
                sent.append((path, json.loads(req.data)))
                body = {}
            else:
                body = {"results": pages[path], "pagination": {"next": None}}
            resp = mock.MagicMock(status=201)
            resp.__enter__.return_value = io.BytesIO(json.dumps(body).encode())
            resp.__enter__.return_value.status = 201
            return resp

        env = {"FLOPPY_URL": "http://f", "SOURCE_TOKEN": "s",
               "LINK_JESS_LIST": "Watch With Jess", "LINK_JESS_TOKEN": "j"}
        with mock.patch("urllib.request.urlopen", urlopen), mock.patch("builtins.print"):
            self.assertTrue(run_once(env))
        self.assertEqual(sent, [("media/tv/tmdb/158756/5/episodes/6/watch/",
                                 {"end_date": "2026-11-24T18:29:00Z", "external_id": "fwt:1909"})])

    def test_load_links(self):
        env = {"LINK_JESS_LIST": "Watch With Jess", "LINK_JESS_TOKEN": "t", "OTHER": "x"}
        self.assertEqual(load_links(env), {"JESS": ("Watch With Jess", "t")})


if __name__ == "__main__":
    unittest.main()
