"""Queue tests use temporary campaign roots and never touch real requests."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from art_queue import ArtQueue, QueueError


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==")


class ArtQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.campaign = Path(self.temp.name)
        self.root = self.campaign / "Website"
        (self.root / "content").mkdir(parents=True)
        (self.root / "content" / "moments.json").write_text('[{"id":"S14-2926"}]', encoding="utf-8")
        (self.root / "art" / "requests").mkdir(parents=True)
        self.portrait = self.campaign / "PCs" / "hero.png"
        self.portrait.parent.mkdir()
        self.portrait.write_bytes(PNG)
        self.queue = ArtQueue(self.root)

    def request(self, job_id="demo", **changes):
        job = dict(schema_version=1, id=job_id, kind="test", moment_id=None, title="Dummy test", prompt="A lantern on a table.", references=[{"path": "PCs/hero.png", "role": "reference portrait"}], alt="A lantern.")
        job.update(changes)
        path = self.root / "art" / "requests" / (job_id + ".json")
        path.write_text(json.dumps(job), encoding="utf-8")
        return path

    def test_fixture_lifecycle_and_no_automatic_retry(self):
        self.request()
        self.assertEqual(self.queue.list()["pending"][0]["id"], "demo")
        claim = self.queue.claim()
        self.assertEqual(claim["resolved_references"][0]["path"], str(self.portrait.resolve()))
        self.assertFalse(self.queue.claim()["claimed"])
        receipt = self.queue.complete("demo", claim["token"], self.portrait)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["request"]["kind"], "test")
        self.assertEqual(receipt["output"], "art/generated/demo.png")
        self.assertEqual(receipt["sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual((self.root / receipt["output"]).read_bytes(), PNG)
        self.assertEqual(len(self.queue.list()["completed"]), 1)
        self.assertFalse(self.queue.claim()["claimed"])
        with self.assertRaisesRegex(QueueError, "already completed"):
            self.queue.complete("demo", claim["token"], self.portrait)

    def test_simultaneous_claims_have_one_winner(self):
        self.request()
        with ThreadPoolExecutor(max_workers=8) as workers:
            claims = list(workers.map(lambda _: ArtQueue(self.root).claim(), range(16)))
        self.assertEqual(sum(claim["claimed"] for claim in claims), 1)
        self.assertEqual(len(self.queue.list()["processing"]), 1)

    def test_claim_picks_only_one_and_skips_invalid(self):
        self.request("a-invalid", prompt="")
        self.request("b-valid")
        self.request("c-valid")
        self.assertEqual(self.queue.claim()["id"], "b-valid")
        self.assertEqual(len(self.queue.list()["pending"]), 1)
        self.assertEqual(len(self.queue.list()["invalid"]), 1)

    def test_wrong_token_cannot_complete_or_fail(self):
        self.request()
        self.queue.claim()
        with self.assertRaisesRegex(QueueError, "Wrong claim token"):
            self.queue.complete("demo", "wrong", self.portrait)
        with self.assertRaisesRegex(QueueError, "Wrong claim token"):
            self.queue.fail("demo", "wrong", "Unavailable")
        self.assertFalse((self.root / "art" / "generated").exists())

    def test_request_edit_blocks_completion(self):
        path = self.request()
        claim = self.queue.claim()
        job = json.loads(path.read_text(encoding="utf-8"))
        job["prompt"] = "A different scene."
        path.write_text(json.dumps(job), encoding="utf-8")
        with self.assertRaisesRegex(QueueError, "changed after claim"):
            self.queue.complete("demo", claim["token"], self.portrait)
        self.assertEqual(len(self.queue.list()["invalid"]), 1)

    def test_invalid_image_does_not_complete(self):
        self.request()
        claim = self.queue.claim()
        fake = self.campaign / "fake.png"
        fake.write_text("Not an image", encoding="utf-8")
        with self.assertRaisesRegex(QueueError, "file signature"):
            self.queue.complete("demo", claim["token"], fake)
        self.assertEqual(len(self.queue.list()["processing"]), 1)
        self.assertFalse((self.root / "art" / "generated").exists())

    def test_format_comes_from_bytes_not_extension(self):
        for job_id, raw, suffix, image_format in (("png", PNG, "png", "png"), ("jpeg", b"\xff\xd8\xff\xe0fixture", "jpg", "jpeg"), ("webp", b"RIFF\x04\x00\x00\x00WEBPfixture", "webp", "webp")):
            with self.subTest(format=image_format):
                self.request(job_id)
                claim = self.queue.claim()
                source = self.campaign / "output.unexpected"
                source.write_bytes(raw)
                receipt = self.queue.complete(job_id, claim["token"], source)
                self.assertEqual(receipt["format"], image_format)
                self.assertTrue(receipt["output"].endswith("." + suffix))

    def test_output_is_never_overwritten(self):
        self.request()
        claim = self.queue.claim()
        output = self.root / "art" / "generated" / "demo.jpg"
        output.parent.mkdir()
        output.write_bytes(b"old interrupted output")
        with self.assertRaisesRegex(QueueError, "already exists"):
            self.queue.complete("demo", claim["token"], self.portrait)
        self.assertEqual(output.read_bytes(), b"old interrupted output")

    def test_failure_has_receipt_and_is_not_retried(self):
        self.request()
        claim = self.queue.claim()
        receipt = self.queue.fail("demo", claim["token"], "Image tool unavailable")
        self.assertEqual(receipt["reason"], "Image tool unavailable")
        self.assertEqual(len(self.queue.list()["failed"]), 1)
        self.assertFalse(self.queue.claim()["claimed"])
        with self.assertRaisesRegex(QueueError, "already failed"):
            self.queue.complete("demo", claim["token"], self.portrait)

    def test_test_and_moment_validation(self):
        self.request("valid-moment", kind="moment", moment_id="S14-2926")
        self.request("missing-moment", kind="moment", moment_id="S99-1234")
        self.request("bad-test", kind="test", moment_id="S14-2926")
        self.request("bad-kind", kind="portrait")
        self.assertEqual([j["id"] for j in self.queue.list()["pending"]], ["valid-moment"])
        self.assertEqual(len(self.queue.list()["invalid"]), 3)

    def test_reference_traversal_and_missing_file_are_invalid(self):
        self.request("escape", references=[{"path": "../outside.png", "role": "hero"}])
        self.request("missing", references=[{"path": "PCs/missing.png", "role": "hero"}])
        self.request("absolute-valid", references=[{"path": str(self.portrait), "role": "hero"}])
        report = self.queue.list()
        self.assertEqual(len(report["invalid"]), 2)
        self.assertEqual(report["pending"][0]["id"], "absolute-valid")
        self.assertTrue(any("escapes" in j["error"] for j in report["invalid"]))

    def test_id_and_filename_validation(self):
        self.request("different", id="other")
        self.request("uppercase", id="BAD")
        self.request("traversal", id="../escape")
        self.request("reserved", id="con")
        self.assertEqual(len(self.queue.list()["invalid"]), 4)
        self.assertFalse(self.queue.claim()["claimed"])
        with self.assertRaises(QueueError):
            self.queue.fail("../escape", "token", "reason")

    def test_state_symlink_cannot_redirect_writes_to_request(self):
        request = self.request()
        state_dir = self.root / "art" / "state"
        state_dir.mkdir()
        try:
            (state_dir / "demo.json").symlink_to(request)
        except OSError:
            self.skipTest("This Windows account cannot create symbolic links")
        before = request.read_bytes()
        self.assertEqual(len(self.queue.list()["invalid"]), 1)
        self.assertFalse(self.queue.claim()["claimed"])
        self.assertEqual(request.read_bytes(), before)

    def test_cli_uses_utf8_with_ascii_environment(self):
        title = "Éowyn — 龍 🐉"
        prompt = "A dragon flies past Éowyn’s lantern."
        self.request(title=title, prompt=prompt)
        command = [sys.executable, str(Path(__file__).with_name("art_queue.py")), "--root", str(self.root)]
        environment = dict(os.environ, PYTHONIOENCODING="ascii")
        result = subprocess.run(command + ["claim"], env=environment, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        claim = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(claim["request"]["title"], title)
        self.assertEqual(claim["request"]["prompt"], prompt)
        self.assertIn(title.encode("utf-8"), result.stdout)
        missing = self.campaign / "missing-龍.png"
        failure = subprocess.run(command + ["complete", "demo", "--token", claim["token"], "--image", str(missing)], env=environment, capture_output=True, check=False)
        self.assertEqual(failure.returncode, 1)
        error = json.loads(failure.stderr.decode("utf-8"))
        self.assertIn("missing-龍.png", error["error"])
        self.assertEqual(len(self.queue.list()["processing"]), 1)


if __name__ == "__main__":
    unittest.main()
