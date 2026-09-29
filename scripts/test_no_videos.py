#!/usr/bin/env python3
"""Exercise the no-video guard in disposable repositories, never the real index."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GUARD = Path(__file__).resolve().with_name("check_no_videos.py")
SPEC = importlib.util.spec_from_file_location("no_videos_guard", GUARD)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isommp42" + bytes(100)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="no-video-guard-")
        self.repo = Path(self.temporary.name)
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith("GIT_"):
                del self.env[key]
        self.env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        self.git("init", "-q")
        self.git("config", "user.name", "Guard Test")
        self.git("config", "user.email", "guard-test@example.invalid")
        self.git("config", "core.hooksPath", str(self.repo / "no-hooks"))

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout

    def add(self, name, data):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.git("add", "-f", "--", name)

    def guard(self, mode="staged", stdin=None):
        return subprocess.run(
            [sys.executable, str(GUARD), mode], cwd=self.repo, env=self.env,
            input=stdin, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def commit(self):
        self.git("commit", "-q", "-m", "test fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def push_check(self, oid=None):
        oid = oid or self.git("rev-parse", "HEAD").decode().strip()
        return self.guard("pre-push", "refs/heads/main " + oid + " refs/heads/main " + "0" * len(oid) + "\n")

    def assert_blocked(self, result, expected):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(expected, result.stderr)

    def test_forced_stage_ignored_video(self):
        (self.repo / ".gitignore").write_text("*.mp4\n", encoding="utf-8")
        self.add("recording.mp4", b"placeholder")
        self.assert_blocked(self.guard(), "recording.mp4")

    def test_uppercase_extension_nested_spaces(self):
        self.add("Session files/Nested Folder/Recording.MP4", b"placeholder")
        self.assert_blocked(self.guard(), "Session files/Nested Folder/Recording.MP4")

    def test_renamed_mp4(self):
        self.add("innocent.dat", MP4)
        self.assert_blocked(self.guard(), "MP4/QuickTime")

    def test_extensionless_mp4(self):
        self.add("recording", MP4)
        self.assert_blocked(self.guard(), "MP4/QuickTime")

    def test_index_checked_even_after_worktree_replaced(self):
        self.add("looks-safe.txt", MP4)
        (self.repo / "looks-safe.txt").write_text("now plain text", encoding="utf-8")
        self.assert_blocked(self.guard(), "MP4/QuickTime")

    def test_png_audio_images_and_typescript_allowed(self):
        samples = {
            "art.png": b"\x89PNG\r\n\x1a\n" + bytes(100),
            "music.mp3": b"ID3" + bytes(100),
            "music.ogg": b"OggS" + bytes(30) + b"OpusHead" + bytes(50),
            "music.wav": b"RIFF" + bytes(4) + b"WAVE" + bytes(100),
            "music.m4a": b"\x00\x00\x00\x18ftypM4A \x00\x00\x00\x00isommp42",
            "art.avif": b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00mif1avif",
            "art.heic": b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic",
            "app.ts": b"export const answer: number = 42;\n",
        }
        for name, data in samples.items():
            self.add(name, data)
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.commit()
        result = self.push_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_transport_stream_with_ts_extension_blocked(self):
        self.add("recording.ts", (b"\x47" + bytes(187)) * 5)
        self.assert_blocked(self.guard(), "MPEG transport")

    def test_ogg_video_blocked(self):
        self.add("recording.ogg", b"OggS" + bytes(30) + b"\x80theora" + bytes(100))
        self.assert_blocked(self.guard(), "Ogg video")

    def test_deleted_historical_video_blocks_push(self):
        self.add("old video.mp4", b"placeholder")
        self.commit()
        self.git("rm", "--", "old video.mp4")
        self.add("notes.txt", b"No video in current tree")
        self.commit()
        self.assertEqual(self.guard().returncode, 0)
        self.assert_blocked(self.push_check(), "old video.mp4")

    def test_renamed_deleted_historical_video_blocks_push(self):
        self.add("old.dat", MP4)
        self.commit()
        self.git("rm", "--", "old.dat")
        self.add("notes.txt", b"Current tree is clean")
        self.commit()
        self.assert_blocked(self.push_check(), "MP4/QuickTime")

    def test_reused_blob_cannot_hide_video_filename(self):
        self.add("safe.txt", b"identical content")
        self.add("renamed.MOV", b"identical content")
        self.commit()
        self.assert_blocked(self.push_check(), "renamed.MOV")

    def test_packed_history_still_blocked(self):
        self.add("old.dat", MP4)
        self.commit()
        self.git("rm", "--", "old.dat")
        self.add("large.bin", b"safe large object\n" * 200000)
        self.commit()
        self.git("gc", "--prune=now")
        self.assert_blocked(self.push_check(), "MP4/QuickTime")

    def test_website_moment_clips_allowed(self):
        self.add("Website/docs/media/video/S34-3598.mp4", MP4)
        self.add("Website/docs/media/video/S34-3598.webp", b"RIFF\x00\x01\x00\x00WEBP" + bytes(50))
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.commit()
        result = self.push_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clip_exception_is_narrow(self):
        for name in ("Website/docs/media/video/Session 34.mp4", "Website/docs/media/S34-3598.mp4",
                     "Website/docs/media/video/nested/S34-3598.mp4", "Session recordings/S34-3598.mp4"):
            with self.subTest(name=name):
                self.git("rm", "-rq", "--cached", "--ignore-unmatch", ".")
                self.add(name, b"placeholder")
                self.assert_blocked(self.guard(), name)

    def test_oversized_clip_blocked(self):
        self.add("Website/docs/media/video/S1-1.mp4", MP4 + bytes(MODULE.MAX_CLIP_SIZE))
        self.assert_blocked(self.guard(), "clip larger than")
        self.commit()
        self.assert_blocked(self.push_check(), "MP4/QuickTime")

    def test_clip_copied_elsewhere_keeps_filename_block(self):
        self.add("Website/docs/media/video/S2-2.mp4", MP4)
        self.add("Session recordings/Session 2.mp4", MP4)
        self.assert_blocked(self.guard(), "Session recordings/Session 2.mp4")
        self.commit()
        self.assert_blocked(self.push_check(), "Session 2.mp4")

    def test_push_deletion_is_allowed(self):
        zeros = "0" * 40
        result = self.guard("pre-push", "(delete) " + zeros + " refs/heads/old " + "a" * 40 + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_push_input_fails_closed(self):
        self.assert_blocked(self.guard("pre-push", "malformed\n"), "operation blocked")

    def test_signature_known_formats(self):
        fixtures = [
            b"\x1a\x45\xdf\xa3" + bytes(100),
            b"RIFF" + bytes(4) + b"AVI " + bytes(100),
            b"FLV" + bytes(100),
            bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c") + bytes(100),
            b".RMF" + bytes(100),
            b"\x00\x00\x01\xba" + bytes(100),
            b"\x00\x00\x00\x01\x67\x42\x00\x1e\xaa\x00\x00\x00\x01\x68\xce\x06\xe2",
            b"\x00\x00\x00\x01\x40\x01\xaa\x00\x00\x00\x01\x42\x01\xaa\xbb\x00\x00\x00\x01\x44\x01\xc0",
        ]
        for fixture in fixtures:
            with self.subTest(header=fixture[:16]):
                self.assertIsNotNone(MODULE.video_signature(fixture))

    def test_embedded_nal_bytes_in_images_do_not_match_raw_video(self):
        nal_bytes = b"\x00\x00\x00\x01\x67\x42\x00\x1e\xaa\x00\x00\x00\x01\x68\xce\x06\xe2"
        for image_header in (b"\xff\xd8\xff\xe0", b"\x89PNG\r\n\x1a\n", b"RIFF\x00\x01\x00\x00WEBP"):
            with self.subTest(header=image_header):
                self.assertIsNone(MODULE.video_signature(image_header + bytes(30) + nal_bytes))

    def test_single_parameter_set_is_not_enough_to_identify_video(self):
        self.assertIsNone(MODULE.video_signature(b"\x00\x00\x00\x01\x67\x42\x00\x1e" + bytes(100)))
        self.assertIsNone(MODULE.video_signature(b"\x00\x00\x00\x01\x40\x01" + bytes(100)))

    def test_real_campaign_images_do_not_match_video(self):
        asset_root = GUARD.parent.parent / "Discord Export" / "Assets"
        names = (
            "1758623443490-b17a8ff6c2a5c132.jpg",
            "%D1%88%D0%BE%D0%BA-acb9225734fd5e0f.png",
        )
        if not all((asset_root / name).is_file() for name in names):
            self.skipTest("Optional campaign image fixtures are not present")
        for name in names:
            with self.subTest(name=name):
                with (asset_root / name).open("rb") as source:
                    data = source.read(MODULE.PREFIX_SIZE)
                self.assertIsNone(MODULE.video_signature(data))
                # The same content must be allowed without a filename extension.
                self.add("image-without-extension", data)
                result = self.guard()
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
