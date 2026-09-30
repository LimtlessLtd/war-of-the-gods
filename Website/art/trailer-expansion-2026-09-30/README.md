# Trailer expansion artwork — 30 September 2026

**20 additional finished widescreen PNGs**, created with built-in image generation and visually reviewed. Together with the [three earlier divine illustrations](../trailer-2026-09-30/README.md), the trailer editor now has 23 new assets from this review.

Open [the local visual gallery](index.html) in a browser, or use the linked originals below. Metadata, SHA-256 hashes, source anchors and individual inspection notes are in [manifest.json](manifest.json). These are direct-request assets, separate from the automated artwork queue. Do not create queue receipts or regenerate completed images.

## Highest-priority replacements

Start with the 220px Nate, Lyrial, Gavin and B.0.B. images, the small `G_CLOCK`, `G_BATTLE`, `G_HAUNT` and `G_MEMORY` images, then the airship and crown sequences. The expansion also adds actual environments for Campess Port and Muttonham, character relationships, the World Tree and the Sea Mother's domain.

The table names keys in the inspected archived `story.py`, not automatic replacement instructions. Match the narration and event before using a shot. `G_MUTTON` does not depict Muttonham, and `G_NYX` is not Nyxara's buried temple; descriptive filenames should replace those misleading associations.

| Image | Suggested shot or source key |
|---|---|
| [Aurilia beneath the long winter](02-aurilia-long-winter.png) | WINTER; MAP atmospheric world shots |
| [Campess Port — where it began](03-campess-port-arrival.png) | new CAMPESS_ESTABLISHING; early world/party transition |
| [Muttonham — a town worth defending](04-muttonham-before-the-siege.png) | new MUTTONHAM_ESTABLISHING; avoid misleading G_MUTTON |
| [Muttonham — hold the fallback line](05-muttonham-fallback-line.png) | G_BATTLE first battle uses |
| [Wavecrest — the town remembers](06-wavecrest-victory.png) | G_CHURCH under the Wavecrest chant |
| [Skycrest — the ancient airship](07-skycrest-above-the-clouds.png) | SKYCREST |
| [The Nimbus Coronet — fire imprisoned in ice](08-nimbus-coronet.png) | GOD_AURIL crown + G_AGNI used for the trapped avatar |
| [Chronos — the still moment aboard ship](09-chronos-the-still-moment.png) | G_CLOCK |
| [Nyxara — the temple beneath Campess Port](10-nyxara-buried-temple.png) | new NYXARA_TEMPLE; do not assume G_NYX is this scene |
| [Mount Mistmourne — the house of ghosts](11-mistmourne-house-exterior.png) | G_HAUNT establishing shot |
| [Nate and Lyrial — the haunted house aftermath](12-the-house-that-kept-them.png) | G_HAUNT; HAUNTED alternative |
| [Nate Wavecrest — captain and warlock](13-nate-wavecrest-portrait.png) | P_NATE |
| [Lyrial Thorne — smuggler and bard](14-lyrial-thorne-portrait.png) | P_LYRIAL |
| [Gavin — the would-be rescuer](15-gavin-prison-yard-portrait.png) | P_GAVIN |
| [The fallen — Nate and Lyrial remembered](16-the-fallen-remembrance.png) | G_MEMORY |
| [Ulrick — the promise he could not keep](17-ulrick-the-promise.png) | ULRICK_EDD emotional alternative |
| [Durzo and Elara — a debt in shadow](18-durzo-and-elara.png) | GHOST; DURZO_P relationship cutaway |
| [Gideon — the World Tree awakens](19-gideon-world-tree-awakening.png) | WORLD_TREE; G_MEMORY alternative for hope transition |
| [D.E.R.E.K. and B.0.B. — aboard Skycrest](20-derek-and-bob-skycrest.png) | P_BOB; BOB_BOLT when no attack is being described; DEREK_P relationship cutaway |
| [Blibdoolpoolp — the abyss answers](21-sea-mother-abyssal-domain.png) | G_BLIB; BLIBG domain reveal alternative |

## Framing and editorial integration

- Originals are 1672 × 941, except Wavecrest at 1672 × 940. They are approximately 16:9 and suitable for the current 1280 × 720 trailer; they are not native 4K. Preserve aspect ratio.
- Add fresh image keys pointing into this directory. Begin with full `(0, 0, 1, 1)` crops and recalculate every subject box. Do not carry over portrait crops, text-panel removal or blurred portrait backgrounds.
- Prefer full-frame holds and restrained moves. Crown tips, the ballista scene's glaive, Wavecrest's raised hand/sword, Chronos's clock and the Sea Mother's crown approach frame edges. Skycrest's upper balloons are already cropped: treat it as a medium-wide detail, not a complete ship silhouette.
- Reassess letterboxing, grading and particle overlays. The ghost-house exterior is already dark. Keep faces and hands clear of captions; add names and all meaningful text in the editor.
- Keep the existing original artwork and video available. These files are candidate replacements, not a rendered revision of the trailer or an automatic website-gallery update.

## Story and continuity limits

All images are illustrations. Public session summaries, existing approved artwork requests and established portraits guided the scenes; generated architectural details and background geography are interpretations, not new campaign facts.

- The Muttonham defence belongs to the first siege in Sessions 15–17. The earlier town view is an establishing illustration, not a canonical street plan or evidence that a destroyed church survived.
- Wavecrest's celebration belongs with the Session 17 chant. It is not a replacement for a shot whose subject is an exploding church.
- Nate and Lyrial's haunted-house aftermath refers to Sessions 33–34. The remembrance image is symbolic, not a resurrection. Their living portraits can be used in introductions or flashbacks.
- Ulrick and his brother are a memory/vision (S34-4496). Durzo and Elara are a symbolic relationship image, not a newly asserted rescue.
- Gideon's World Tree image illustrates the beginning of renewal in Session 57 (S57-9626), not an already restored entire forest. The ring itself is too small to read clearly.
- D.E.R.E.K. and B.0.B. preserve their contrasting sizes, single blue eyes and red lips. The grapes and relationship are established, but the exact helm composition, distant city and second airship are illustrative. Do not use it to illustrate an attack.
- The Nimbus Coronet's distant ice architecture is symbolic, not a mapped destination. The Sea Mother scene is a domain manifestation, not a new recorded ship encounter.

## Aurilia map: draft withheld

The AI widescreen outpaint changed fine lettering and geographic details. It failed the preservation check and is **not included among these 20 deliverables**. The authoritative `docs/media/map/aurilia.jpg` and map pins remain unchanged. Number 01 was reserved for that draft; accepted assets retain IDs 02–21.

An exact composite could preserve the original 2048 × 1536 map as the central layer and use generated ocean/parchment around it, with no new named territories. That optional follow-up remains pending the user's requested compositing preference. The winter panorama can cover atmospheric world narration, but cannot substitute for a geographic map shot.

## Handoff and verification

Use the [earlier editing brief](../trailer-2026-09-30/README.md) for the critique, pantheon layout and proposed dialogue-led three-minute structure. Prioritise original god performances and verified session audio; more stills alone will not solve the pacing. This batch does not add transcripts, audio excerpts or invented quotations.

All 20 accepted PNGs were visually inspected, decoded and checked against the hashes in the manifest after copying. No new trailer render or website build has been run for this artwork-only change. Private references and exact prompts remain on the original workstation in `Trailer Video/expansion-2026-09-30/prompts.json`; the rejected map draft is there too. The public originals and this handoff can be used independently by a remote editor.

## Individual review notes

### Aurilia beneath the long winter

Reviewed: coherent winter panorama, visible patrol and warm settlements; interpretive environment, not map-accurate geography.

### Campess Port — where it began

Reviewed: readable harbour, warmer southern-coast palette, no labels; generic dock workers, interpretive architecture.

### Muttonham — a town worth defending

Reviewed: modest walled market town, river and mountains; interpretive earlier establishing view, architecture is not a canonical town plan.

### Muttonham — hold the fallback line

Reviewed: Ulrick and Durzo identities retained, readable barricade and ballista, approaching ice forces; glaive tip near top edge, avoid extra crop.

### Wavecrest — the town remembers

Reviewed: Nate likeness and clothing retained; readable celebration and knight salute; raised hand and sword meet upper edge, avoid top crop. Crowd and knight appearance are illustrative.

### Skycrest — the ancient airship

Reviewed: coherent ornate airship and propellers, warm cabin lights, no weapons firing. Upper balloons are cropped by the generator; use as a medium-wide view, not an entire-ship silhouette.

### The Nimbus Coronet — fire imprisoned in ice

Reviewed: icy crown, enclosed flame, open casket and airship deck all readable. Distant ice architecture is symbolic background, not a canonical flight location.

### Chronos — the still moment aboard ship

Reviewed: original bespectacled Chronos retained, ship setting, readable grandfather clock and suspended motion. Decorative marks on foreground scroll are not campaign text; clock top touches edge.

### Nyxara — the temple beneath Campess Port

Reviewed: hooded white-eyed Nyxara, flooded ancient sanctuary, clean central composition. Temple architecture is interpretive; no extra living deity.

### Mount Mistmourne — the house of ghosts

Reviewed: clear ominous doorway, mountain context and restrained ghosts; exterior architecture is interpretive. Dark image benefits from gentle grading, not further darkening.

### Nate and Lyrial — the haunted house aftermath

Reviewed: two distinct established characters, non-graphic death scene and ghosts. Feet extend toward frame edges; retain faces and resting hands during reframing.

### Nate Wavecrest — captain and warlock

Reviewed: red hair, human ears, navy coat, pendant and stubble retained; left region available for title. Symbolic living portrait, not a newly claimed event.

### Lyrial Thorne — smuggler and bard

Reviewed: half-elf ears, braids, green eyes, brown leather, coin and lute readable. Symbolic portrait; decorative coin markings are not campaign inscriptions.

### Gavin — the would-be rescuer

Reviewed: rugged face, brown hood and plain equipment retained; cold prison setting and readable face. Detailed interpretation from a small 220px source.

### The fallen — Nate and Lyrial remembered

Reviewed: both likenesses retained, soft symbolic memory treatment, no generated names or dates. No literal resurrection implied; editor adds memorial typography.

### Ulrick — the promise he could not keep

Reviewed: Ulrick likeness and armour retained, restrained expression, coherent clasped gauntlets and brother mostly off-frame. Use as memory/vision illustration, not current battle aftermath.

### Durzo and Elara — a debt in shadow

Reviewed: Durzo retains silver hair and red-black clothing; Elara remains an indistinct violet apparition. Symbolic relationship image, not a new literal rescue scene.

### Gideon — the World Tree awakens

Reviewed: fairy scale, insect wings and dark robes retained; first green growth climbs a largely dead World Tree. Ring is too small to read clearly. Illustrative Session 57 awakening.

### D.E.R.E.K. and B.0.B. — aboard Skycrest

Reviewed: distinct single blue eyes, red lips and correct father/son scale. Grapes readable. Scenic background includes another airship and a fanciful mountain city; use as symbolic relationship montage, not an exact voyage record.

### Blibdoolpoolp — the abyss answers

Reviewed: skeletal sea-witch identity, skull/driftwood crown, serpent forms and small vessel are readable. Crown tips reach top edge despite requested margin; preserve full frame. Symbolic domain image, not an actual new ship encounter.
