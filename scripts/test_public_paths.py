#!/usr/bin/env python3
"""Exercise the public-path guard in disposable repositories, never the real index."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GUARD = Path(__file__).resolve().with_name("check_public_paths.py")


class PublicPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="public-path-guard-")
        self.repo = Path(self.temporary.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        self.git("init", "-q")
        self.git("config", "user.name", "Guard Test")
        self.git("config", "user.email", "guard-test@example.invalid")
        self.git("config", "core.hooksPath", str(self.repo / "no-hooks"))

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def add(self, name, data=b"x"):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.git("add", "-f", "--", name)

    def commit(self):
        self.git("commit", "-q", "-m", "fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def guard(self, mode="staged", stdin=None):
        return subprocess.run([sys.executable, str(GUARD), mode], cwd=self.repo, env=self.env,
                              input=stdin, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def push_check(self):
        oid = self.git("rev-parse", "HEAD").decode().strip()
        return self.guard("pre-push", "refs/heads/main " + oid + " refs/heads/main " + "0" * len(oid) + "\n")

    def test_website_and_guards_allowed(self):
        for name in ("Website/docs/index.html", "scripts/check_public_paths.py", ".github/workflows/pages.yml",
                     ".gitignore", "GIT_SETUP.md", "LICENSE"):
            self.add(name)
        self.assertEqual(self.guard().returncode, 0, self.guard().stderr)
        self.commit()
        result = self.push_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_private_folders_blocked_even_when_forced(self):
        for name in ("War of the Gods Notes.txt", "Handouts/Letter.png", "Discord Export/general.json", "DM/index.html"):
            with self.subTest(name=name):
                self.git("rm", "-rq", "--cached", "--ignore-unmatch", ".")
                self.add(name)
                result = self.guard()
                self.assertEqual(result.returncode, 1)
                self.assertIn(name, result.stderr)

    def test_deleted_private_file_in_history_blocks_push(self):
        self.add("Gods/Nyxara.md")
        self.commit()
        self.git("rm", "-q", "--", "Gods/Nyxara.md")
        self.add("Website/README.md")
        self.commit()
        self.assertEqual(self.guard().returncode, 0)
        result = self.push_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Gods/Nyxara.md", result.stderr)

    def test_lookalike_names_blocked(self):
        self.add("Website2/secret.txt")
        self.add("websitex")
        result = self.guard()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Website2/secret.txt", result.stderr)

    def test_invalid_push_input_fails_closed(self):
        result = self.guard("pre-push", "malformed\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("operation blocked", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
