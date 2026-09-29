# Campaign artwork handoff

Claude prepares scene requests. A Codex routine uses built-in image generation, saves each result, and records completion. The website build attaches completed artwork to its matching moment. This setup does not call an image API, launch Claude, or publish the website.

## Files and ownership

| Location | Purpose | Writer |
| --- | --- | --- |
| `art/requests/<job-id>.json` | One self-contained image request | Claude or the user |
| `art/state/<job-id>.json` | Claim, completion or failure receipt | Queue helper, invoked by Codex |
| `art/generated/<job-id>.<extension>` | Original generated image | Queue helper, invoked by Codex |
| `art/examples/` | Templates; never processed automatically | Either agent |
| `art/ROUTINE_PROMPT.md` | Instructions to paste into a local Codex routine | User configures the routine |
| `CLAUDE_HANDOFF.md` | Pickup note for Claude | Codex |

All paths above are relative to `E:\DnD\War of the Gods\Website`. Portrait paths inside requests are relative to the campaign root (`E:\DnD\War of the Gods`), for example `PCs/Fiddle.jpg`. Absolute reference paths are also accepted if they stay inside that campaign root.

## Prepare a real scene

1. Start from `art/examples/moment-request.example.json`, outside the live queue.
2. Replace every placeholder. Use a unique lowercase job ID with hyphens, and the exact existing moment ID from `content/moments.json`. The job ID and filename must match.
3. Write a complete visual prompt grounded in events already revealed to the players. Describe the characters, action, location, framing, style and appearance constraints. Do not include unrevealed DM material. Identify each reference's role and only include relevant portraits. References guide consistency; they do not guarantee a perfect likeness.
4. Set `kind` to `moment`, provide useful image alt text, then save the finished JSON to `art/requests/<job-id>.json`. For safe delivery, write a temporary non-JSON filename first and rename it when complete.
5. Run `python tools/art_queue.py list` and fix any validation errors before the routine picks it up.

Putting a valid request in the queue makes it eligible for generation and local site integration. The example template is intentionally not a valid, queued request. A `kind: "test"` job never appears on the campaign website.

## Worker lifecycle

Run commands from the Website directory:

```powershell
python tools/art_queue.py list
python tools/art_queue.py claim
```

`claim` atomically reserves one pending job and returns its request snapshot, token and resolved reference paths. If it returns `claimed: false`, there is no work. Two workers cannot claim the same job.

The agent then reads any reference images with its image-viewing tool, invokes built-in image generation once, inspects the result and completes the job using the actual saved image file:

```powershell
python tools/art_queue.py complete JOB-ID --token CLAIM-TOKEN --image 'ABSOLUTE_PATH_RETURNED_BY_IMAGE_TOOL'
```

The helper copies the selected image into `art/generated`, checks the format, records a SHA-256 digest and writes a completion receipt. It will not replace an existing output. It rejects changed requests or incorrect claim tokens.

If generation fails, the tool is unavailable, or required inputs cannot be used:

```powershell
python tools/art_queue.py fail JOB-ID --token CLAIM-TOKEN --reason 'Short description of the problem'
```

The Python helper coordinates files; it cannot call Codex's image tool itself. It must run inside an agent session with image generation available. There is no API-key fallback in this workflow.

## Recovery and revisions

Requests become immutable once claimed. Keep referenced portrait files unchanged while a job is processing: the request freezes their paths, not their image bytes. Completed, failed and processing jobs are not automatically retried. This avoids charging usage again after a crash or uncertain response.

For a stuck processing job, establish that the original worker has stopped, then inspect the receipt and the previous run. If a finished image exists at the image tool's original output path and `art/generated` has no output for this job, complete the original claim with that file and token. If a crash already left an orphan image under `art/generated` but the receipt is still processing, inspect that image, move it to a new safe file under this project's `scratch/art-recovery`, then complete the original claim using that saved file. The helper deliberately refuses to overwrite the orphan in place. Resolve and verify both move paths stay within the project first; never replace an existing recovery file. A stale `art/locks/<job-id>.lock` also needs manual inspection and removal only after the original worker has stopped. No new generation is needed when the finished image can be recovered.

If there is no usable output, mark the original job failed. After understanding the failure, create a corrected request with a fresh ID, such as `scene-name-v2`. Do not blindly delete state files or requeue everything.

Use a new job ID for a requested revision. When more than one completed image targets a moment, the build uses the newest completion (job ID breaks ties). Keep old originals for reference.

## Website integration

```powershell
python tools/build.py
```

The build reads completed receipts, verifies the output file's location and digest, copies eligible images into `docs/media/art`, and attaches artwork metadata to existing moments. Moment cards are shared between the moments view and session pages. Test jobs, unfinished jobs and invalid outputs are excluded. Source `content/moments.json` is not rewritten. Prompts, local reference paths and state tokens are not added to public site data.

Rebuilding is local. Committing and pushing remain separate actions. The routine does not deploy. A dedicated Art gallery is not part of this initial handoff.

To validate the site without rewriting the working build, use `python tools/build.py --output-dir <temporary-folder>`.

## Routine setup

Create a **local** routine for this project (or a scheduled follow-up in this chat), using the prompt in `art/ROUTINE_PROMPT.md`. Use the same Website checkout that Claude writes to, not a separate worktree. Suggested cadence: every 15 minutes while actively preparing artwork; reduce it when the queue is rarely used. The worker processes at most one image per run and stays quiet when nothing changes.

Keep the computer awake and Codex open. Built-in image generation uses the account's usage allowance. If image generation is unavailable or a limit is reached, report the problem and do not switch to the separately billed API.

## Verification

```powershell
python -m unittest discover -s tools -p 'test_art*.py'
```

See `art/TEST_REPORT.md` for the actual dummy run, its saved image and any limitations. The routine itself is supplied as a prompt for the user to configure; it is not enabled by creating these files.
