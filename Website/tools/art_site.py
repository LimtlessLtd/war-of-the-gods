"""Include completed campaign artwork in a static build, without exposing prompts."""
import hashlib
import io
import json
from pathlib import Path
import re


# (key, longest side, WebP quality): pages show these; the original stays as the full-size link
SIZES = (('web', 1600, 82), ('thumb', 640, 78))


def web_copies(image, original, output_dir):
    """Write smaller WebP copies next to the published original and return their public metadata.

    Without Pillow, or for an image it cannot read, pages fall back to the original.
    """
    try:
        from PIL import Image
        picture = Image.open(io.BytesIO(image))
        picture.load()
    except Exception:
        return {}
    extra = {'w': picture.width, 'h': picture.height}
    picture = picture.convert('RGB')
    for key, longest, quality in SIZES:
        path = original.with_name(f'{original.stem}-{key}.webp')
        if not path.exists():
            copy = picture.copy()
            copy.thumbnail((longest, longest), Image.LANCZOS)
            copy.save(path, 'WEBP', quality=quality, method=6)
        extra[key] = path.relative_to(output_dir).as_posix()
    return extra


def attach_art(moments, root, output_dir):
    """Copy verified artwork and return moments with public-only art metadata.

    Test jobs, incomplete receipts, unknown moments, and invalid outputs are
    deliberately absent from the published data. Source moments are not mutated.
    """
    root, output_dir = Path(root), Path(output_dir)
    generated = (root / 'art' / 'generated').resolve()
    known = {m['id'] for m in moments}
    chosen = {}
    for path in sorted((root / 'art' / 'state').glob('*.json')):
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            if receipt.get('schema_version') != 1 or receipt.get('status') != 'completed':
                continue
            request = receipt['request']
            if request.get('schema_version') != 1 or request.get('kind') != 'moment':
                continue
            request_id, moment_id = request['id'], request['moment_id']
            if not isinstance(request_id, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', request_id):
                continue
            if receipt.get('id') != request_id or path.stem != request_id or moment_id not in known:
                continue
            relative = Path(receipt['output'])
            if relative.is_absolute() or relative.parts[:2] != ('art', 'generated'):
                continue
            source = (root / relative).resolve()
            if not source.is_relative_to(generated) or not source.is_file():
                continue
            extension = source.suffix.lower()
            if extension not in ('.png', '.jpg', '.jpeg', '.webp'):
                continue
            image = source.read_bytes()
            digest = hashlib.sha256(image).hexdigest()
            if digest != receipt['sha256']:
                continue
            completed = receipt.get('completed_at', '')
            if not isinstance(completed, str):
                continue
            # The most recently completed version wins, with an ID tie-breaker.
            rank = (completed, request_id)
            if moment_id in chosen and rank <= chosen[moment_id][0]:
                continue
            alt = request.get('alt')
            if not isinstance(alt, str) or not alt.strip():
                continue
            chosen[moment_id] = (rank, image, {
                'src': f'media/art/{request_id}-{digest[:12]}{extension}',
                'alt': alt.strip(),
                'request_id': request_id,
            })
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            # An unfinished write or broken receipt must not break the website.
            continue

    artwork = {}
    for moment_id, (_, image, metadata) in chosen.items():
        destination = output_dir / metadata['src']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(image)
        metadata.update(web_copies(image, destination, output_dir))
        artwork[moment_id] = metadata
    return [dict(moment, **({'art': artwork[moment['id']]} if moment['id'] in artwork else {}))
            for moment in moments]
