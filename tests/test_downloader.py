import unittest
from unittest.mock import patch

from downloader import build_filename, parse_args, prompt_for_playlist_url, sanitize_filename


class TestDownloader(unittest.TestCase):
    def test_sanitize_filename_replaces_invalid_chars(self):
        self.assertEqual(sanitize_filename('Artist/Name:Title?*<>|'), 'Artist_Name_Title_____')

    def test_build_filename_defaults_unknown(self):
        self.assertEqual(build_filename(1, '', ''), '01_unknown_artist - unknown_title')

    def test_parse_args_with_playlist_url(self):
        args = parse_args(['https://soundcloud.com/user/sets/playlist'])
        self.assertEqual(args.playlist_url, 'https://soundcloud.com/user/sets/playlist')
        self.assertIsNone(args.output)

    def test_parse_args_without_playlist_url_returns_none(self):
        args = parse_args([])
        self.assertIsNone(args.playlist_url)
        self.assertIsNone(args.output)

    @patch('builtins.input', return_value=' https://soundcloud.com/user/sets/test ')
    def test_prompt_for_playlist_url_strips_value(self, mock_input):
        self.assertEqual(prompt_for_playlist_url(), 'https://soundcloud.com/user/sets/test')


if __name__ == '__main__':
    unittest.main()
