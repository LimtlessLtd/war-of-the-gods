# Git setup, public paths and video protection

This repository is public. It carries only the campaign website (`Website/`) and
the guards that keep it that way. `.gitignore` is an allowlist of top-level names,
and `scripts/check_public_paths.py` blocks commits and pushes of anything else, so
DM notes, handouts, gods, PCs, the Discord export, maps, tokens and the private DM
site stay on this computer. The earlier history, which held the whole campaign
folder, is kept in the private repo `LimtlessLtd/war-of-the-gods-archive`.

Video files also stay local.
`.gitignore` skips common video extensions. The tracked hooks also reject video
filenames (including uppercase extensions) and recognizable video content stored
under another name. `.ts` TypeScript and `.ogg` audio files are allowed unless
their content is recognized as video. Generic MP4/QuickTime containers, including
`.m4a` clips, are allowed only when complete track metadata confirms every track
is audio. Missing, malformed, unknown or video track metadata remains blocked.

One exception: the campaign website's moment clips, named like `S34-3598.mp4`
directly inside `Website/docs/media/video/`, are committed so GitHub Pages can
serve them. Each must be 25 MiB or smaller (they are cut at 720p and are usually
1-10 MB), so a full session recording is still blocked even if renamed into that
folder. Videos anywhere else are blocked as before.

After cloning, install Python 3.9 or newer and enable the hooks in that clone:

```sh
git config core.hooksPath .githooks
python scripts/check_no_videos.py staged
python scripts/check_public_paths.py staged
```

The commit hook reads the index, so `git add -f` does not evade it. The push hook
checks the full history reachable from outgoing refs, including videos deleted in
a later commit. If it rejects a historical video, removing that file only from
the latest commit is insufficient: remove it from the outgoing history too.

Loose Git objects are inspected by decompressing only a small header. Packed
objects are streamed with bounded memory; scanning a large packed history can
take longer. Suspected MP4 audio is streamed from the exact Git blob into a
temporary file so track metadata at the end is also checked without loading the
whole media file into memory. The guard requires Python and fails closed if it
cannot finish.

These protections are local: Git does not automatically enable hooks after a
clone, and `--no-verify` or changing the hook configuration can bypass them.
Signature checks cover common formats, not every possible video encoding or
videos inside archives. This is not a GitHub server-side upload restriction.

Run the isolated verification suites with:

```sh
python scripts/test_no_videos.py
python scripts/test_public_paths.py
```
