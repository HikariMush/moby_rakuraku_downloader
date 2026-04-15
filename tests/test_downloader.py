import unittest
from unittest.mock import patch

from pathlib import Path
from downloader import (
    build_filename,
    download_playlist,
    download_track,
    parse_args,
    parse_track_selection_input,
    prompt_for_playlist_url,
    sanitize_filename,
    validate_audio_settings,
)


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

    def test_validate_audio_settings_allows_mp3_bitrate(self):
        self.assertEqual(validate_audio_settings('mp3', '320'), '320')

    def test_validate_audio_settings_rejects_invalid_bitrate(self):
        with self.assertRaises(ValueError):
            validate_audio_settings('mp3', '500')

    def test_validate_audio_settings_ignores_wav_bitrate(self):
        self.assertIsNone(validate_audio_settings('wav', '320'))

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

    @patch('downloader.yt_dlp.YoutubeDL')
    def test_download_track_does_not_set_bitrate_for_wav(self, mock_youtube_dl):
        download_track(
            'https://soundcloud.com/user/test',
            '/tmp/out',
            Path('/usr/bin/ffmpeg'),
            audio_format='wav',
            audio_bitrate='320',
        )
        called_opts = mock_youtube_dl.call_args[0][0]
        self.assertEqual(called_opts['postprocessors'][0]['preferredcodec'], 'wav')
        self.assertNotIn('preferredquality', called_opts['postprocessors'][0])

    @patch('builtins.input', return_value=' https://soundcloud.com/user/sets/test ')
    def test_prompt_for_playlist_url_strips_value(self, mock_input):
        self.assertEqual(prompt_for_playlist_url(), 'https://soundcloud.com/user/sets/test')

    def test_parse_track_selection_input_all(self):
        self.assertEqual(parse_track_selection_input('', 3), [1, 2, 3])

    def test_parse_track_selection_input_range_and_list(self):
        self.assertEqual(parse_track_selection_input('1,3-4', 5), [1, 3, 4])

    def test_parse_track_selection_input_invalid(self):
        with self.assertRaises(ValueError):
            parse_track_selection_input('a,b', 3)

    @patch('downloader.fetch_track_info')
    @patch('downloader.download_track')
    def test_download_playlist_selected_tracks(self, mock_download_track, mock_fetch_track_info):
        mock_fetch_track_info.return_value = {'ext': 'mp3', 'abr': 192}
        playlist_info = {
            'title': 'Test Playlist',
            'entries': [
                {'url': 'https://soundcloud.com/track1', 'title': 'Track 1', 'uploader': 'Artist 1'},
                {'url': 'https://soundcloud.com/track2', 'title': 'Track 2', 'uploader': 'Artist 2'},
                {'url': 'https://soundcloud.com/track3', 'title': 'Track 3', 'uploader': 'Artist 3'},
            ],
        }

        metadata, report_path = download_playlist(
            'https://soundcloud.com/user/sets/test',
            Path('/tmp'),
            Path('/usr/bin/ffmpeg'),
            audio_format='mp3',
            audio_bitrate='192',
            playlist_info=playlist_info,
            selected_track_indices=[1, 3],
            log_callback=lambda msg: None,
            progress_callback=lambda current, total, track_info: None,
        )

        self.assertEqual(metadata['downloaded_count'], 2)
        self.assertEqual(metadata['not_selected_count'], 1)
        self.assertEqual(metadata['total_tracks'], 3)
        self.assertEqual(metadata['tracks'][1]['status'], 'not_selected')
        self.assertEqual(metadata['tracks'][1]['reason'], 'user_not_selected')
        self.assertTrue(report_path.exists())


if __name__ == '__main__':
    unittest.main()
