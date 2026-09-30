# War of the Gods

The campaign site for the War of the Gods table: every session, the map, the best moments and the Discord chaos.
Published with GitHub Pages from the `docs/` folder.

## Updating after a session

1. Add the session to `content/sessions.json` (and its location in `content/locations.json`, play date in `content/dates.json`).
2. Add its best moments to `content/moments.json` (`s`, `t` start second, `d` length, `title`, optional `lines` and `quote`).
3. `python tools/clips.py` cuts the audio clips from the local recordings in `Session recordings/` (needs `pip install av numpy`).
4. `python tools/transcribe.py` transcribes any new clips into `content/transcripts.json` (needs `pip install faster-whisper`).
5. Read each new transcript and tag the moment in `content/moments.json`:
   `pcs` (hero ids from `content/heroes.json`), `kind` (`funny` or `epic`), `stars` (1–5, decides the hero pages' top three)
   and a one-sentence `blurb` of what happens in the clip. Only attribute a `quote` when the speaker is clear.
6. `python tools/build.py` rebuilds `docs/index.html` and `docs/data/site.json`.
7. Commit and push to `main`. The *Publish campaign site* workflow redeploys GitHub Pages in a minute or two.

The transcripts and the recordings are the source of truth: blurbs describe what can be heard in the clip, nothing more.

## Heroes

`content/heroes.json` holds every player character and companion (`group`: `party`, `companion` or `fallen`).
Each hero page (`#/hero/<id>`) is built from it: top three epic and funny moments by `stars`, quotes, every tagged
moment, and "the story so far", which is every sentence of `sessions.json` that mentions one of the hero's `match` names.

## Publishing

GitHub Pages serves `Website/docs` through `.github/workflows/pages.yml`. One-time setup: in the repository's
Settings → Pages, set *Source* to **GitHub Actions**. The site is `noindex`, but anyone with the link can see it.

Discord pictures: export the channels with DiscordChatExporter (JSON, download assets) to
`Discord Export/` in the campaign folder, then run `python tools/discord_import.py index`, `sheets`,
mark keepers in `content/discord_review.json` (`"<messageId>:<fileIndex>": "keep"` or `"skip"`), and `publish`.
Keep only posts about the campaign: art of the characters, things that happened at the table, maps and handouts.
Each post is filed under the most recent session played before it (`content/dates.json`).

## Layout

- `content/` source data and page fragments
- `tools/` build and import scripts
- `docs/` the published site (generated, plus media)

## Trailer

The home page's *Watch the trailer* button plays `docs/media/video/trailer.mp4` (poster `trailer.webp` beside it)
in the lightbox. The build adds it only when the file is there. It is the one video allowed besides the moment clips:
exactly that path, up to 95 MiB (see `GIT_SETUP.md`), so encode it for the web (720p H.264, about 1.3 Mbps).

## Campaign artwork

The shared Claude/Codex image workflow is described in [art/README.md](art/README.md).
Claude's pickup note is [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md); the user-configured
Codex routine prompt is [art/ROUTINE_PROMPT.md](art/ROUTINE_PROMPT.md).
Completed scene images are included by the normal build. Test jobs never appear on the site.

The build also writes two WebP copies of each image next to the original: `-web` (1600 px) for the lightbox and
`-thumb` (640 px) for the page. The pages use them, and the original stays as the "Full size" link. This needs
Pillow (`pip install pillow`); without it the pages fall back to the original. Each painting appears in the
**Painted** tab, on its moment card, on its session in the timeline and on the pages of the heroes in it
(the best one becomes the hero page backdrop). A random painting sits behind the home page title.
