#!/usr/bin/env python3
"""Block video filenames and recognizable video headers in actual Git objects.

Staged mode checks the complete index. Pre-push mode checks every object reachable
from each outgoing ref, including earlier commits where a video was later removed.
Loose objects usually need only a bounded prefix decompressed; packed objects are
streamed through one cat-file process with bounded memory. Suspected MP4 audio is
checked from the complete Git blob using a temporary file. No third-party packages
needed.

Two exceptions, both directly inside Website/docs/media/video/: the campaign
website's short moment clips, named like S34-3598.mp4 and no larger than
MAX_CLIP_SIZE, and the one campaign trailer, exactly trailer.mp4 and no larger than
MAX_TRAILER_SIZE. Full session recordings are gigabytes, so the size caps keep them
out even if renamed into that folder. Video filenames anywhere else are still blocked.
"""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zlib


VIDEO_EXTENSIONS = frozenset(
    ".mp4 .m4v .mov .qt .avi .mkv .webm .wmv .asf .flv .f4v "
    ".mpeg .mpg .mpe .mpv .m1v .m2v .m2p .m2t .m2ts .mts .vob .ogv "
    ".3gp .3g2 .divx .xvid .rm .rmvb .yuv .h264 .h265 .hevc .mxf "
    ".bik .bk2 .roq".split()
)
# .ts is also TypeScript and .ogg is often audio: inspect their content instead.
PREFIX_SIZE = 65536
CHUNK_SIZE = 65536
MAX_TREE_SIZE = 64 * 1024 * 1024
OID_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
CLIP_DIR = b"Website/docs/media/video"
CLIP_NAME = re.compile(rb"S\d{1,3}-\d{1,6}\.mp4\Z")
MAX_CLIP_SIZE = 25 * 1024 * 1024
TRAILER_PATH = CLIP_DIR + b"/trailer.mp4"
MAX_TRAILER_SIZE = 50 * 1024 * 1024


def allowed_size(path):
    """The largest video allowed at this path, or 0 where videos are not allowed."""
    if path == TRAILER_PATH:
        return MAX_TRAILER_SIZE
    folder, _, name = path.rpartition(b"/")
    return MAX_CLIP_SIZE if folder == CLIP_DIR and CLIP_NAME.match(name) else 0


def git(*args):
    result = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def display(path):
    return path.decode("utf-8", "backslashreplace") if isinstance(path, bytes) else str(path)


def video_extension(path):
    # Work with Git's bytes so unusual filenames do not change the decision.
    suffix = path.rsplit(b"/", 1)[-1].rsplit(b".", 1)
    return len(suffix) == 2 and ("." + suffix[1].decode("ascii", "ignore").lower()) in VIDEO_EXTENSIONS


def video_signature(data):
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "Matroska/WebM container"
    if data[:4] in (b"RIFF", b"RIFX") and data[8:12] in (b"AVI ", b"AVIX", b"AMV "):
        return "AVI container"
    if data.startswith(b"FLV"):
        return "Flash video container"
    if data.startswith(bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")):
        return "ASF/Windows Media container"
    if data.startswith(b".RMF"):
        return "RealMedia container"
    if data.startswith(b"OggS") and (b"\x80theora" in data or b"\x01video\x00" in data):
        return "Ogg video stream"
    if data.startswith(b"\x00\x00\x01") and len(data) > 3 and data[3] in (0xBA, 0xB3, 0xB0):
        return "MPEG video/program stream"
    if data.startswith(bytes.fromhex("060e2b34020501010d010201")):
        return "MXF container"
    if data[:3] == b"BIK" or data[:3] == b"KB2":
        return "Bink video"
    if data.startswith(b"\x84\x10\xff\xff\xff\xff\x1e\x00"):
        return "RoQ video"

    # MPEG transport packets may start after a timestamp or a short lead-in.
    for packet_size in (188, 192, 204):
        candidate_end = min(packet_size, max(0, len(data) - 4 * packet_size))
        offset = data.find(b"G", 0, candidate_end)
        while offset >= 0:
            if all(data[offset + packet * packet_size] == 0x47 for packet in range(1, 5)):
                return "MPEG transport stream"
            offset = data.find(b"G", offset + 1, candidate_end)

    # ISO BMFF brands identify MP4/QuickTime, but also legitimate images/audio.
    # Permit explicit image/audio major brands; generic isom/mp4 containers are
    # conservative matches because identifying their tracks needs more than a header.
    non_video_brands = {
        b"avif", b"avis", b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis",
        b"mif1", b"msf1", b"M4A ", b"M4B ", b"M4P ", b"F4A ", b"F4B ",
    }
    offset = 0
    while offset + 16 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        kind = data[offset + 4:offset + 8]
        header_size = 8
        if size == 1:
            size = int.from_bytes(data[offset + 8:offset + 16], "big")
            header_size = 16
        if kind == b"ftyp":
            brand = data[offset + header_size:offset + header_size + 4]
            if len(brand) == 4 and brand not in non_video_brands:
                return "MP4/QuickTime container"
            return None
        if kind in (b"moov", b"mdat", b"wide"):
            return "QuickTime/media container"
        if kind not in (b"free", b"skip", b"uuid") or size < header_size:
            break
        offset += size

    # Annex B must begin the file (possibly after leading zero bytes). Searching
    # arbitrary image/audio payloads for a single NAL-like value is not reliable:
    # those byte sequences also occur in valid compressed images. Require an
    # ordered pair of parameter-set NALs and consistent headers instead.
    if re.match(b"\x00{2,16}\x01", data):
        starts = [match.end() for match in re.finditer(b"\x00\x00(?:\x00)?\x01", data[:4096])]
        units = [data[start:(starts[index + 1] - 3 if index + 1 < len(starts) else min(len(data), 4096))]
                 for index, start in enumerate(starts)]
        units = units[:16]
        h264_types = [unit[0] & 0x1F for unit in units if unit]
        if (len(h264_types) == len(units) and h264_types
                and h264_types[0] in (6, 7, 9)
                and all(not unit[0] & 0x80 and 1 <= kind <= 23
                        for unit, kind in zip(units, h264_types))):
            for index, kind in enumerate(h264_types[:-1]):
                if (kind == 7 and h264_types[index + 1] == 8
                        and len(units[index]) >= 4 and len(units[index + 1]) >= 2
                        and units[index][0] & 0x60 and units[index + 1][0] & 0x60):
                    return "raw H.264 video"
        h265_types = [(unit[0] >> 1) & 0x3F for unit in units if len(unit) >= 2]
        if (len(h265_types) == len(units) and h265_types
                and h265_types[0] in (32, 33, 35, 39)
                and all(not unit[0] & 0x80 and unit[1] & 7 and kind <= 40
                        for unit, kind in zip(units, h265_types))):
            if any(h265_types[index:index + 2] == [33, 34]
                   and len(units[index]) >= 4 and len(units[index + 1]) >= 3
                   for index in range(len(h265_types) - 1)):
                return "raw H.265 video"
    return None


def audio_only_mp4(source):
    """Confirm every declared track is audio, including metadata after media data."""
    source.seek(0, os.SEEK_END)
    file_end = source.tell()
    box_count = 0

    def boxes(start, end):
        nonlocal box_count
        offset = start
        while offset < end:
            box_count += 1
            if box_count > 100000 or end - offset < 8:
                raise ValueError("Invalid or excessive MP4 boxes")
            source.seek(offset)
            header = source.read(8)
            if len(header) != 8:
                raise ValueError("Truncated MP4 box")
            size = int.from_bytes(header[:4], "big")
            kind = header[4:8]
            header_size = 8
            if size == 1:
                extended = source.read(8)
                if len(extended) != 8:
                    raise ValueError("Truncated extended MP4 box")
                size = int.from_bytes(extended, "big")
                header_size = 16
            elif size == 0:
                size = end - offset
            if kind == b"uuid":
                header_size += 16
            if size < header_size or size > end - offset:
                raise ValueError("MP4 box exceeds its enclosing bounds")
            yield kind, offset + header_size, offset + size
            offset += size

    def audio_media(start, end):
        handlers = 0
        for kind, payload, box_end in boxes(start, end):
            if kind != b"hdlr":
                continue
            handlers += 1
            if handlers != 1 or box_end - payload < 24:
                return False
            source.seek(payload)
            header = source.read(12)
            if header[:4] != bytes(4) or header[8:12] != b"soun":
                return False
        return handlers == 1

    def audio_track(start, end):
        media_boxes = 0
        for kind, payload, box_end in boxes(start, end):
            if kind == b"mdia":
                media_boxes += 1
                if media_boxes != 1 or not audio_media(payload, box_end):
                    return False
        return media_boxes == 1

    movies = 0
    tracks = 0
    try:
        for kind, payload, box_end in boxes(0, file_end):
            if kind == b"ftyp" and (box_end - payload < 8 or (box_end - payload) % 4):
                return False
            if kind != b"moov":
                continue
            movies += 1
            if movies != 1:
                return False
            for child, child_payload, child_end in boxes(payload, box_end):
                if child == b"trak":
                    tracks += 1
                    if not audio_track(child_payload, child_end):
                        return False
        return movies == 1 and tracks > 0
    except ValueError:
        return False


def blob_video_signature(oid, prefix):
    signature = video_signature(prefix)
    if signature not in ("MP4/QuickTime container", "QuickTime/media container"):
        return signature
    # Read the indexed/historical object, never the possibly different worktree.
    # Redirecting cat-file into a seekable temporary file keeps RAM usage bounded
    # while allowing moov metadata at the end of arbitrarily sized media blobs.
    with tempfile.TemporaryFile() as source:
        result = subprocess.run(
            ["git", "cat-file", "blob", oid], stdout=source,
            stderr=subprocess.PIPE, check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
        if audio_only_mp4(source):
            return None
    return signature


class ObjectReader:
    """Read only a prefix of loose blobs; stream/drain packed blobs if necessary."""

    def __init__(self):
        self.objects = Path(os.fsdecode(git("rev-parse", "--git-path", "objects").strip()))
        self.hash_bytes = 32 if git("rev-parse", "--show-object-format").strip() == b"sha256" else 20
        self.batch = None

    def close(self):
        if self.batch is not None:
            self.batch.stdin.close()
            try:
                self.batch.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.batch.kill()
                self.batch.wait()
            self.batch.stdout.close()

    def read(self, oid):
        loose_path = self.objects / oid[:2] / oid[2:]
        if loose_path.is_file():
            with loose_path.open("rb") as source:
                inflater = zlib.decompressobj()
                unpacked = bytearray()
                goal = PREFIX_SIZE + 128
                header_end = -1
                kind = None
                size = None
                while len(unpacked) < goal:
                    compressed = inflater.unconsumed_tail or source.read(CHUNK_SIZE)
                    if not compressed:
                        break
                    unpacked.extend(inflater.decompress(compressed, goal - len(unpacked)))
                    if header_end < 0 and b"\x00" in unpacked:
                        header_end = unpacked.index(0)
                        kind, size_text = bytes(unpacked[:header_end]).split(b" ", 1)
                        size = int(size_text)
                        if kind == b"tree" and size > MAX_TREE_SIZE:
                            raise RuntimeError("Git tree exceeds the guard's 64 MiB safety limit")
                        goal = header_end + 1 + (size if kind == b"tree" else min(size, PREFIX_SIZE))
                if header_end < 0 or len(unpacked) < goal:
                    raise RuntimeError("Could not read Git object " + oid)
                return kind, bytes(unpacked[header_end + 1:goal]), size

        if self.batch is None:
            self.batch = subprocess.Popen(
                ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
        self.batch.stdin.write(oid.encode("ascii") + b"\n")
        self.batch.stdin.flush()
        header = self.batch.stdout.readline().strip().split()
        if len(header) != 3:
            raise RuntimeError("Could not read Git object " + oid)
        _, kind, size_text = header
        size = int(size_text)
        if kind == b"tree" and size > MAX_TREE_SIZE:
            raise RuntimeError("Git tree exceeds the guard's 64 MiB safety limit")
        keep = size if kind == b"tree" else min(size, PREFIX_SIZE)
        prefix = self._read_exact(keep)
        remaining = size - keep
        while remaining:
            count = min(CHUNK_SIZE, remaining)
            self._read_exact(count)
            remaining -= count
        if self.batch.stdout.read(1) != b"\n":
            raise RuntimeError("Unexpected end of Git object " + oid)
        return kind, prefix, size

    def _read_exact(self, size):
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.batch.stdout.read(size - len(chunks))
            if not chunk:
                raise RuntimeError("Unexpected end of git cat-file output")
            chunks.extend(chunk)
        return bytes(chunks)


def staged_entries():
    for entry in git("ls-files", "--stage", "-z").split(b"\x00"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        if stage != b"0":
            raise RuntimeError("Resolve index conflicts before committing")
        # A gitlink references another repository; it is not a local blob.
        if mode != b"160000":
            yield oid.decode("ascii"), path


def tree_entries(data, hash_bytes):
    offset = 0
    while offset < len(data):
        space = data.index(b" ", offset)
        end = data.index(b"\x00", space)
        mode = data[offset:space]
        name = data[space + 1:end]
        oid_end = end + 1 + hash_bytes
        if oid_end > len(data):
            raise RuntimeError("Malformed Git tree")
        if mode not in (b"40000", b"160000"):
            yield name
        offset = oid_end


def outgoing_tips():
    tips = set()
    for line in sys.stdin:
        fields = line.strip().split()
        if not fields:
            continue
        if len(fields) != 4 or not OID_PATTERN.fullmatch(fields[1]):
            raise RuntimeError("Invalid pre-push ref input")
        local_oid = fields[1]
        if local_oid.strip("0"):
            tips.add(local_oid)
    return sorted(tips)


def check(mode):
    findings = []
    seen = set()
    reader = ObjectReader()
    try:
        if mode == "staged":
            entries = list(staged_entries())
            # Approve clips and the trailer first so the result does not depend on
            # index order. Each allowed path is checked against its own size cap.
            sizes = {}
            for oid, path in entries:
                if allowed_size(path) and oid not in sizes:
                    kind, _, size = reader.read(oid)
                    sizes[oid] = size if kind == b"blob" else None

            def fits(oid, limit):
                return sizes.get(oid) is not None and sizes[oid] <= limit

            clips = {oid for oid, path in entries if allowed_size(path) and fits(oid, allowed_size(path))}
            for oid, path in entries:
                limit = allowed_size(path)
                if limit and not fits(oid, limit):
                    what = "trailer" if path == TRAILER_PATH else "clip"
                    findings.append(display(path) + " (" + what + " larger than " + str(limit >> 20) + " MiB)")
                elif video_extension(path) and not limit:
                    findings.append(display(path) + " (video filename)")
                if oid in seen or oid in clips:
                    continue
                seen.add(oid)
                kind, data, _ = reader.read(oid)
                signature = blob_video_signature(oid, data) if kind == b"blob" else None
                if signature:
                    findings.append(display(path) + " (" + signature + ")")
            seen |= clips
        else:
            tips = outgoing_tips()
            if not tips:
                return 0
            # Do not exclude remote commits: historical videos must not be missed.
            # Each object is listed once, with the first path Git reached it by.
            for line in git("rev-list", "--objects", *tips, "--").splitlines():
                if not line:
                    continue
                raw_oid, _, path = line.partition(b" ")
                oid = raw_oid.decode("ascii", "replace")
                if not OID_PATTERN.fullmatch(oid):
                    raise RuntimeError("Unexpected git rev-list output")
                if oid in seen:
                    continue
                seen.add(oid)
                kind, data, size = reader.read(oid)
                if kind == b"tree":
                    for name in tree_entries(data, reader.hash_bytes):
                        if video_extension(name) and not allowed_size(path + b"/" + name):
                            findings.append(display(name) + " (video filename in historical tree " + oid[:12] + ")")
                elif kind == b"blob":
                    if allowed_size(path) and size <= allowed_size(path):
                        continue
                    signature = blob_video_signature(oid, data)
                    if signature:
                        findings.append(oid[:12] + " (" + signature + " in outgoing history)")
    finally:
        reader.close()
    if findings:
        print("Blocked: videos are not allowed in this repository.", file=sys.stderr)
        for finding in findings[:30]:
            print("  " + finding, file=sys.stderr)
        if len(findings) > 30:
            print("  ... and " + str(len(findings) - 30) + " more matches", file=sys.stderr)
        print("Remove video files from the index; videos already committed must also be removed from outgoing history.", file=sys.stderr)
        return 1
    print("No-video guard: checked " + str(len(seen)) + " Git objects.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("staged", "pre-push"))
    args = parser.parse_args()
    try:
        return check(args.mode)
    except (OSError, RuntimeError, ValueError, zlib.error) as error:
        print("No-video guard could not complete; operation blocked: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
