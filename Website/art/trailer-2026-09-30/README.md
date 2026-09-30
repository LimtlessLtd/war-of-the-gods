# Trailer artwork and editing brief — 30 September 2026

Three finished images created by Codex with built-in image generation at the user's request. The user subsequently requested that the finished work be pushed to this repository. These assets are separate from the automated artwork queue: no queue requests or completion receipts are required. They are available to the trailer editor but are not automatically included in the website gallery.

## Images

| Image | Editorial purpose |
|---|---|
| [Six gods and their domains](pantheon-six-domains-v1.png) | Replacement for the old six-gods painting. Use as a full-frame pantheon reveal or a brief return before the final choice. |
| [Fire against winter](fire-against-winter-v1.png) | Agni's returning fire against Auril's dominion. Use with the war premise or escalating divine stakes. |
| [Life and shadow](life-and-shadow-v1.png) | Nyxara and Gaia across the life/death boundary. Use for Gideon's dual connection and the cycle of life and death. |

All three are native **1672 × 941 RGB PNGs**, approximately 16:9, suitable for full-frame use in the current 1280 × 720 trailer. They are not native 4K or upscaled images. File sizes and SHA-256 hashes are in [manifest.json](manifest.json).

These are symbolic campaign illustrations. The two paired scenes do not establish that a literal confrontation or meeting happened in a recorded session.

## Critique and proposed direction

The existing trailer runs approximately 9:03. The review used sampled frames throughout the local copy, Claude's edit sources, local campaign assets and transcripts, and machine transcription of selected recordings. It was not a complete real-time listening pass on the finished mix; final delivery and audio balance remain unassessed.

The strongest ingredients are the campaign artwork, divine conflict, real table dialogue, humour and moments of loss. The main opportunity is to build the edit around the gods' existing performances and the players' choices.

1. **Reach the party sooner.** Roughly the first 2½ minutes establish the world and pantheon before the party introduction. Start with a strong voice, threat or choice within the opening seconds.
2. **Let the gods speak.** Replace substantial narrator biographies with short threats, bargains or offers from the original reveal recordings. The existing cut already contains gods and some session dialogue; the improvement is in how those performances drive scenes.
3. **Interleave gods and champions.** Connect Agni with Ulrick, Nyxara with Durzo, Gaia/Nyxara with Gideon, the Sea Mother with Fiddle, and Chronos with D.E.R.E.K. and B.0.B. Let Auril's threat connect the sequence.
4. **Vary the visual treatment.** Repeated paintings, blurred portrait backgrounds, particles and slow reframing diminish contrast. Mix original reveal footage, meaningful details and a few actual-play shots that last long enough to read. The old montage's four seconds of sixteen tabletop screenshots provides little time to understand an event.
5. **Concentrate the emotional beat.** Keep one strong passage of grief or loss, with breathing room, then show the choice it motivates. Preserve the longer memorial material for an extended retrospective.
6. **Improve caption readability.** Sampled dialogue captions were tiny italic text in the lower black bar. Check at phone size; increase size and contrast, shorten lines and give them enough time.
7. **Shorten the ending.** The source reserves 12½ seconds for the title and another 26 seconds for its stinger. A shorter title hold and one brief unresolved beat would preserve momentum.

Suggested main cut: **2½–3 minutes**. Retain the longer version as an extended campaign retrospective if desired.

| Approximate time | Purpose |
|---|---|
| 00:00–00:12 | A divine hook from an existing performance. |
| 00:12–00:30 | Auril's threat and concrete stakes. |
| 00:30–01:20 | Gods interwoven with champions, choices and humour. |
| 01:20–01:40 | One emotional consequence. |
| 01:40–02:35 | Rising action led by session dialogue and reactions. |
| 02:35–02:50 | An unanswered consequential choice. |
| 02:50–03:00 | Brief title and one final button. |

Start with a dialogue-only rough cut, then add only necessary narrator bridges, followed by music and images. Match reactions to their actual context; cross-session pairings should read as montage rather than invented conversations. Preserve character attribution: the whale exploding into rats is a Nate scene, while Fiddle has his own whale rescue material.

At the time of review, `Website/content/transcripts.json` contained 135 entries for 207 listed moments. Those are selected-clip transcripts, not complete session transcripts. Some important dramatic scenes lack entries, some timing segments are coarse, and one inspected transcript extends past its listed clip duration. Use moment metadata to locate candidate windows in the original recordings, then confirm words, speaker and trim points by listening.

## Pantheon layout and identity

| Position | God | Visual cues |
|---|---|---|
| Upper left | Nyxara | Black hood, narrow spectral mask, white eyes and scythe; souls, tombs and shadow. |
| Upper middle | Auril | White hair, blue face and eyes, ice/skull crown; glacier citadel and disciplined ranks. |
| Upper right | Blibdoolpoolp | Skeletal sea-witch, seaweed hair and skull/driftwood crown; storm seas, serpentine shapes, ships and abyssal depths. |
| Lower left | Chronos | Brown/grey beard, swept hair, round spectacles and scholar's coat; clocks, sand, astronomical rings and threads. |
| Lower middle | Agni | Grey beard, bronze armour, red mantle, flame halo and axe; fire, forge architecture and golden scales. |
| Lower right | Gaia | Pale green face, branch crown and root/leaf form; forests, waterfalls, wildlife and new growth. |

The new images draw on established reveal appearances. In particular, Chronos is a bespectacled scholar. Nyxara's masked white-eyed face, Blibdoolpoolp's skeletal sea-worn face and Gaia's living green appearance remain distinct.

## Trailer source integration

The inspected archived `story.py` refers to the old six-gods painting as `IMG['SONG']`, with `media/discord/1427757501776003195_0.webp` as its source. It also contains `CROP['SONG']` and several `BOX['SONG.*']` regions tied to that old image.

**Do not swap only the file path.** The old `CROP['SONG'] = (0, 0, 1, 0.81)` removes the lower 19%, damaging the new lower row. Chronos is now lower left and Agni lower middle, so old subject coordinates also need replacing.

- Add new image keys such as `PANTHEON_DOMAINS_V1`, `FIRE_WINTER_V1`, and `LIFE_SHADOW_V1`, resolving the PNGs relative to this repository.
- Start the pantheon at full `(0, 0, 1, 1)` framing. Replace old SONG shots selectively and inspect every shot that used a subject crop.
- The separate `PANTH` image includes gods and heroes. This new pantheon contains no player-character portraits, so it is not a direct substitute for a shot introducing champions.
- Use individual reveal footage or portraits for close-ups. Enlarging one sixth of the group image loses detail.
- Reassess grading, bloom, particles, zoom punches and letterboxing. The images already contain strong lighting and fine detail.
- Add names and domain labels in the editor where needed. No text is baked into the PNGs.

## Inspection notes

- All three returned images were visually inspected and decoded successfully; hashes were checked after copying into the repository.
- Pantheon: exactly six principal deities, distinct faces and domains, no visible lettering or panel borders. Auril's crown tips and Nyxara's scythe approach the top edge. Preserve the full image; the requested safety margin was not fully achieved.
- Fire/winter: both identities are readable, with strong warm/cold contrast. Auril appears as a monumental manifestation integrated into the citadel rather than a fully visible seated body.
- Life/shadow: an organic transition connects the two environments; the river and sapling reinforce the cycle. Nyxara's scythe approaches the left edge. The figures' gestures do not establish a new alliance.
- These are asset checks, not validation of a newly rendered trailer. The video has not been replaced by this change.

## Local source material

On the original campaign workstation, `Trailer Video/review/TRAILER_CRITIQUE.md` contains the extended critique and candidate recording timestamps. `Trailer Video/art-2026-09-30/` contains the original generated PNGs, full prompts, reference frames and additional integration notes. These local sources are not included in this public repository. This README and the three PNGs can be used independently by a remote editor.
