import unittest
from unittest.mock import patch

from pathlib import Path
from downloader import build_filename, download_track, parse_args, prompt_for_playlist_url, sanitize_filename


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
        self.assertEqual(args.format, 'mp3')
        self.assertEqual(args.bitrate, '192')

    def test_parse_args_with_format_and_bitrate(self):
        args = parse_args(['https://soundcloud.com/user/sets/playlist', '--format', 'wav', '--bitrate', '320'])
        self.assertEqual(args.playlist_url, 'https://soundcloud.com/user/sets/playlist')
        self.assertEqual(args.format, 'wav')
        self.assertEqual(args.bitrate, '320')

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_track_uses_requested_format_and_bitrate(self, mock_youtube_dl):
        mock_ydl = mock_youtube_dl.return_value.__enter__.return_value
        download_track(
            'https://soundcloud.com/user/test',
            '/tmp/out',
            Path('/usr/bin/ffmpeg'),
            audio_format='mp3',
            audio_bitrate='320',
        )
        self.assertTrue(mock_youtube_dl.called)
        called_opts = mock_youtube_dl.call_args[0][0]
        self.assertEqual(called_opts['postprocessors'][0]['preferredcodec'], 'mp3')
        self.assertEqual(called_opts['postprocessors'][0]['preferredquality'], '320')

    @patch('builtins.input', return_value=' https://soundcloud.com/user/sets/test ')
    def test_prompt_for_playlist_url_strips_value(self, mock_input):
        self.assertEqual(prompt_for_playlist_url(), 'https://soundcloud.com/user/sets/test')


if __name__ == '__main__':
    unittest.main()
