"""Local artwork handoff; stores jobs and receipts, never invokes an image service.

Run `python tools/art_queue.py --help`. Paths default to this Website directory.
Processing/failed jobs are never automatically retried: an image may already exist.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import sys
import uuid


class QueueError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inside(path, base):
    # Windows may preserve its extended prefix if a file appears while resolve()
    # is running. Normalize that spelling so concurrent claims compare equally.
    def canonical(value):
        text = str(value.resolve())
        if text.startswith("\\\\?\\UNC\\"):
            text = "\\\\" + text[8:]
        elif text.startswith("\\\\?\\"):
            text = text[4:]
        return Path(text)

    resolved = canonical(path)
    if not resolved.is_relative_to(canonical(base)):
        raise QueueError(f"Path escapes {base}: {path}")
    return resolved


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class ArtQueue:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.campaign = self.root.parent
        self.art = inside(self.root / "art", self.root)
        if self.art != self.root / "art":
            raise QueueError("The art directory must not be redirected")

    def path(self, folder, name=""):
        directory = inside(self.art / folder, self.art)
        if directory != self.art / folder:
            raise QueueError(f"Queue folder must not be redirected: {folder}")
        return inside(directory / name, directory)

    @staticmethod
    def check_id(job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", job_id):
            raise QueueError("id must be a lowercase slug (letters, digits, single hyphens)")
        if len(job_id) > 100 or job_id.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}:
            raise QueueError("id is too long or is a reserved filename")

    def read_request(self, path):
        path = inside(path, self.path("requests"))
        raw = path.read_bytes()
        job = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(job, dict):
            raise QueueError("request must be a JSON object")
        self.check_id(job.get("id"))
        if path.name != job["id"] + ".json":
            raise QueueError("request filename must match id")
        if type(job.get("schema_version")) is not int or job["schema_version"] != 1:
            raise QueueError("schema_version must be 1")
        if job.get("kind") not in ("test", "moment"):
            raise QueueError("kind must be test or moment")
        for field in ("title", "prompt", "alt"):
            if not isinstance(job.get(field), str) or not job[field].strip():
                raise QueueError(f"{field} must be nonempty text")
        if "moment_id" not in job:
            raise QueueError("moment_id is required (null for a test)")
        if job["kind"] == "test":
            if job["moment_id"] is not None:
                raise QueueError("test jobs must have moment_id null")
        else:
            if not isinstance(job["moment_id"], str) or not job["moment_id"]:
                raise QueueError("moment jobs require a moment_id")
            moments = json.loads((self.root / "content" / "moments.json").read_text(encoding="utf-8-sig"))
            if not isinstance(moments, list) or job["moment_id"] not in {m.get("id") for m in moments if isinstance(m, dict)}:
                raise QueueError(f"Unknown moment_id: {job['moment_id']}")
        if not isinstance(job.get("references"), list):
            raise QueueError("references must be a list")
        references = []
        for reference in job["references"]:
            if not isinstance(reference, dict) or any(not isinstance(reference.get(k), str) or not reference[k].strip() for k in ("path", "role")):
                raise QueueError("each reference requires nonempty path and role")
            candidate = Path(reference["path"])
            resolved = inside(candidate if candidate.is_absolute() else self.campaign / candidate, self.campaign)
            if not resolved.is_file():
                raise QueueError(f"Reference file missing: {reference['path']}")
            references.append({"path": str(resolved), "role": reference["role"]})
        return job, hashlib.sha256(raw).hexdigest(), references

    def read_state(self, job_id):
        state = json.loads(self.path("state", job_id + ".json").read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema_version") != 1 or state.get("id") != job_id or state.get("status") not in ("processing", "completed", "failed"):
            raise QueueError("Invalid state receipt; inspect it manually")
        return state

    def list(self):
        report = {key: [] for key in ("pending", "processing", "completed", "failed", "invalid")}
        requests = sorted(self.path("requests").glob("*.json"))
        for path in requests:
            try:
                job, digest, _ = self.read_request(path)
                entry = {"id": job["id"], "kind": job["kind"], "moment_id": job["moment_id"], "title": job["title"]}
                status = "pending"
                if self.path("state", job["id"] + ".json").exists():
                    state = self.read_state(job["id"])
                    if state.get("request_sha256") != digest or state.get("request") != job:
                        raise QueueError("Request changed after claim; do not retry it automatically")
                    status = state["status"]
                    entry.update({k: state[k] for k in ("output", "reason", "claimed_at", "completed_at", "failed_at") if k in state})
                report[status].append(entry)
            except (ValueError, OSError) as error:
                report["invalid"].append({"file": str(path), "error": str(error)})
        names = {p.name for p in requests}
        for path in sorted(self.path("state").glob("*.json")):
            if path.name not in names:
                report["invalid"].append({"file": str(path), "error": "State has no request; inspect it manually"})
        return report

    def claim(self):
        report = self.list()
        for entry in report["pending"]:
            job_id = entry["id"]
            job, digest, references = self.read_request(self.path("requests", job_id + ".json"))
            state = {"schema_version": 1, "id": job_id, "status": "processing", "token": secrets.token_hex(24), "request_sha256": digest, "request": job, "claimed_at": now()}
            path = self.path("state", job_id + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                # Exclusive creation chooses one worker even when claims overlap.
                with path.open("xb") as handle:
                    handle.write(encode(state))
            except FileExistsError:
                continue
            return {"claimed": True, "id": job_id, "token": state["token"], "request": job, "request_sha256": digest, "resolved_references": references, "state_path": str(path)}
        return {"claimed": False, "invalid": report["invalid"]}

    @contextmanager
    def transition(self, job_id):
        self.check_id(job_id)
        lock = self.path("locks", job_id + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write(now())
        except FileExistsError as error:
            raise QueueError("Job transition is locked; inspect a stale lock manually") from error
        try:
            yield
        finally:
            lock.unlink()

    def owned_state(self, job_id, token):
        state = self.read_state(job_id)
        if state["status"] != "processing":
            raise QueueError(f"Job is already {state['status']}; it cannot be completed or failed again")
        if not isinstance(state.get("token"), str) or not secrets.compare_digest(state["token"], token):
            raise QueueError("Wrong claim token")
        return state

    def write_state(self, job_id, state):
        path = self.path("state", job_id + ".json")
        temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(encode(state))
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def complete(self, job_id, token, image):
        with self.transition(job_id):
            state = self.owned_state(job_id, token)
            job, digest, _ = self.read_request(self.path("requests", job_id + ".json"))
            if digest != state.get("request_sha256") or job != state.get("request"):
                raise QueueError("Request changed after claim; completion refused")
            with Path(image).open("rb") as source:
                header = source.read(12)
                if header.startswith(b"\x89PNG\r\n\x1a\n"):
                    image_format, extension = "png", "png"
                elif header.startswith(b"\xff\xd8\xff"):
                    image_format, extension = "jpeg", "jpg"
                elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                    image_format, extension = "webp", "webp"
                else:
                    raise QueueError("Image must have a PNG, JPEG, or WebP file signature")
                output = self.path("generated", job_id + "." + extension)
                output.parent.mkdir(parents=True, exist_ok=True)
                # Do not overwrite even an orphan left by an interrupted completion.
                if any(self.path("generated", job_id + "." + ext).exists() for ext in ("png", "jpg", "webp")):
                    raise QueueError("Output already exists; inspect it manually to avoid duplicate work")
                sha = hashlib.sha256()
                try:
                    with output.open("xb") as target:
                        source.seek(0)
                        while chunk := source.read(1024 * 1024):
                            target.write(chunk)
                            sha.update(chunk)
                except FileExistsError as error:
                    raise QueueError("Output already exists; refusing overwrite") from error
                except OSError:
                    output.unlink(missing_ok=True)
                    raise
            state.update(status="completed", output=output.relative_to(self.root).as_posix(), sha256=sha.hexdigest(), format=image_format, completed_at=now())
            self.write_state(job_id, state)
            return state

    def fail(self, job_id, token, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise QueueError("Failure reason must be nonempty text")
        with self.transition(job_id):
            state = self.owned_state(job_id, token)
            state.update(status="failed", reason=reason, failed_at=now())
            self.write_state(job_id, state)
            return state


def main():
    # Receipt JSON and CLI JSON use the same encoding, including when Windows
    # pipes inherit an ASCII or legacy code page from the scheduler.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Website root (defaults to this script's project)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Show pending, processing, completed, failed and invalid jobs")
    commands.add_parser("claim", help="Claim at most one pending job; never retries")
    complete = commands.add_parser("complete", help="Save generated image and completion receipt")
    complete.add_argument("id")
    complete.add_argument("--token", required=True)
    complete.add_argument("--image", type=Path, required=True)
    failed = commands.add_parser("fail", help="Record a failure without scheduling a retry")
    failed.add_argument("id")
    failed.add_argument("--token", required=True)
    failed.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        queue = ArtQueue(args.root)
        if args.command == "list":
            result = queue.list()
        elif args.command == "claim":
            result = queue.claim()
        elif args.command == "complete":
            result = queue.complete(args.id, args.token, args.image)
        else:
            result = queue.fail(args.id, args.token, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
