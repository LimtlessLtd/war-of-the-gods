# Pickup note for Claude — 28 September 2026

The user ran out of Claude usage and asked Codex to set up the shared-folder image workflow, perform a dummy test, leave you a note, and provide a routine prompt for them to configure. This note records that work; it does not authorize publishing or new campaign content.

## How to resume

1. Read `art/README.md` and `art/TEST_REPORT.md`.
2. Run `python tools/art_queue.py list` from this Website directory.
3. Continue discovering and verifying epic moments with the campaign sources available to you. The artwork setup has not selected, fabricated, or added any real moments.
4. For each scene the user wants illustrated, fill out `art/examples/moment-request.example.json`, then save it as `art/requests/<unique-job-id>.json`. Use an exact existing moment ID from `content/moments.json`. Only include events already revealed at the table and the relevant portrait references. Reference paths such as `PCs/Fiddle.jpg` resolve from the campaign root, not from Website.
5. Codex's worker will claim a queued request, generate an image using its built-in image tool, save the original to `art/generated`, and write a completion receipt under `art/state`. Read those receipts to see results; do not rewrite them yourself while a worker may be active.
6. `python tools/build.py` integrates completed real artwork into matching moment cards, including their appearance on session pages. The build copies the eligible image into `docs/media/art`. It ignores the dummy test. An Art gallery remains an optional later feature.

## Rules of the handoff

- You own new scene requests; Codex owns generation and result receipts. This avoids both agents editing one shared status file.
- A valid request in the live queue is eligible for generation. Keep drafts/templates in `art/examples` until finished.
- Requests are immutable after claiming. For a revision, use a fresh job ID (for example `scene-name-v2`) with the same moment ID. The newest completed revision is used by the build.
- Failed or processing jobs do not retry automatically. Follow `art/README.md` to recover an interrupted job without generating duplicates.
- Prompts and portraits guide visual consistency, but actual likeness matching still needs inspection.
- The queue helper is a file coordinator, not an image API client. A Codex agent with the image tool processes it. There is no OpenAI API key in this setup.
- The user received `art/ROUTINE_PROMPT.md` to configure their own local schedule. Do not assume the schedule is already enabled. Claude does not need to be running for Codex to process queued jobs.
- No Slack or Discord bridge is configured, and saving a file does not wake Claude. You pick up this note and receipts when you resume.

## Existing work preserved

At setup, `content/moments.json` already contained uncommitted additions and dozens of audio files under `docs/media/audio` were untracked. Codex did not alter, stage, commit, discard or publish those files. Site validation uses a separate output directory so it does not regenerate the active `docs/index.html` or `docs/data/site.json` during setup.

The exact dummy-run result and automated checks are recorded in `art/TEST_REPORT.md`. No real campaign image has been requested by this setup, and no commit, push or deployment has been performed.

## Artwork continuation — 29 September 2026

The user explicitly requested processing as many remaining queued images as possible and leaving the local checkout ready for their GitHub commit/push. This manual continuation completed all seven remaining requests, sequentially with one built-in image-generation call each: `cyclopean-cog`, `front-door-unlocked`, `geronimo-cannonball`, `lethargic-leviathan`, `master-vampire-falls-v2`, `the-first-grape`, and `the-l-volume`. Every resolved portrait was opened before generation. Originals and immutable completion receipts are in `art/generated` and `art/state`; the request snapshots and prompts remain in the receipts.

The final local build succeeded: 60 sessions, 135 moments, 235 posts, 15 campaign artworks. All 16 completed originals (including the excluded pipeline test) match their receipt SHA-256. All 15 public artwork originals, WebP display copies and thumbnails were verified. No pending, processing or invalid jobs remain. The old failed `master-vampire-falls` receipt is retained for history; its separately queued v2 succeeded. Do not retry or reset the old failure.

Validation: 21 artwork tests ran, 20 passed and one Windows symlink-permission test was skipped. `git diff --check` passed. No tracked or non-ignored untracked file is 50 MiB or larger. Generated site data includes public artwork metadata only, and excludes the pipeline test.

Visual review note: `geronimo-cannonball` depicts Fiddle face-down rather than on his back. The image remains usable and was retained without regeneration. Any desired revision should use a fresh request ID.

The checkout remains on `main`, uncommitted and unstaged. Existing content/code changes were preserved. Include the relevant `art/requests`, `art/state`, `art/generated`, `docs/media/art`, rebuilt `docs/index.html` and `docs/data/site.json`, and this handoff in the user's eventual commit, alongside their existing website work as appropriate. No commit, push, deployment or external messages were performed.
