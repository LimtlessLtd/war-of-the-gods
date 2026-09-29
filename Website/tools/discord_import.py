"""Import pictures from a DiscordChatExporter (JSON + downloaded assets) export.

  python tools/discord_import.py index     -> scratch/discord_index.json (every message with a picture or video)
  python tools/discord_import.py sheets    -> scratch/sheets/*.jpg contact sheets to review, numbered
  python tools/discord_import.py publish   -> docs/media/discord/* + content/discord.json for the items marked
                                              "keep" in content/discord_review.json

Message text is treated as plain data. It is escaped when shown on the site and never interpreted.
"""
import json, os, sys, glob, re, shutil, datetime
from PIL import Image, ImageDraw, ImageFont, ImageSequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPAIGN = os.path.dirname(ROOT)  # the War of the Gods folder this Website lives in
EXPORT = os.path.join(CAMPAIGN, 'Discord Export')
SCRATCH = os.path.join(ROOT, 'scratch')
OUT_MEDIA = os.path.join(ROOT, 'docs', 'media', 'discord')
IMG = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
VID = ('.mp4', '.mov', '.webm')


def exports():
    for f in sorted(glob.glob(os.path.join(EXPORT, '*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception as e:  # still being written, or not an export
            print('skip', os.path.basename(f), e)
            continue
        if 'messages' in d:
            yield f, d


def local(path, base):
    if not path or path.startswith('http'):
        return None
    p = os.path.normpath(os.path.join(base, path.replace('%20', ' ').replace('\\', '/')))
    return p if os.path.exists(p) else None


def index():
    items = []
    for f, d in exports():
        ch = d['channel']['name']
        base = os.path.dirname(f)
        for m in d['messages']:
            files = []
            for a in m.get('attachments', []):
                p = local(a.get('url'), base)
                ext = os.path.splitext(a.get('fileName', '') or (p or ''))[1].lower()
                if p and (ext in IMG or ext in VID):
                    files.append(dict(path=p, name=a.get('fileName'), size=a.get('fileSizeBytes', 0), kind='vid' if ext in VID else 'img'))
            if not files:
                continue
            au = m.get('author', {})
            items.append(dict(
                id=m['id'], ch=ch, t=m['timestamp'], a=au.get('nickname') or au.get('name'), aid=au.get('id'),
                x=(m.get('content') or '').strip(), react=sum(r.get('count', 0) for r in m.get('reactions', [])),
                pinned=m.get('isPinned', False), files=files))
    items.sort(key=lambda i: i['t'])
    os.makedirs(SCRATCH, exist_ok=True)
    json.dump(items, open(os.path.join(SCRATCH, 'discord_index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    n = sum(len(i['files']) for i in items)
    print(f"{len(items)} messages with {n} files ({sum(1 for i in items for x in i['files'] if x['kind'] == 'vid')} videos)")


def thumb(path, size):
    im = Image.open(path)
    try:
        im.seek(0)
    except EOFError:
        pass
    im = im.convert('RGB')
    im.thumbnail((size, size))
    return im


def sheets(per=24, cols=6, cell=260):
    items = json.load(open(os.path.join(SCRATCH, 'discord_index.json'), encoding='utf-8'))
    flat = [(i, j, f) for i in items for j, f in enumerate(i['files'])]
    out = os.path.join(SCRATCH, 'sheets')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    font = ImageFont.load_default(size=15)
    keymap = []
    for s in range(0, len(flat), per):
        chunk = flat[s:s + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * cell, rows * (cell + 22)), (20, 24, 30))
        dr = ImageDraw.Draw(sheet)
        for k, (i, j, f) in enumerate(chunk):
            x, y = (k % cols) * cell, (k // cols) * (cell + 22)
            num = s + k
            try:
                if f['kind'] == 'img':
                    im = thumb(f['path'], cell - 8)
                else:
                    import av
                    c = av.open(f['path'])
                    fr = next(c.decode(video=0)).to_image()
                    c.close()
                    fr.thumbnail((cell - 8, cell - 8))
                    im = fr
                sheet.paste(im, (x + (cell - im.width) // 2, y + 4 + (cell - 8 - im.height) // 2))
            except Exception as e:
                dr.text((x + 8, y + 100), f'unreadable {e}'[:40], fill=(200, 80, 80), font=font)
            tag = f"#{num} {'VID ' if f['kind'] == 'vid' else ''}{i['t'][:10]} {(i['a'] or '')[:12]}"
            dr.rectangle((x, y + cell - 4, x + cell, y + cell + 20), fill=(12, 16, 22))
            dr.text((x + 6, y + cell - 2), tag, fill=(240, 144, 74), font=font)
            keymap.append(dict(n=num, id=i['id'], j=j))
        sheet.save(os.path.join(out, f'sheet_{s // per:03d}.jpg'), quality=72)
    json.dump(keymap, open(os.path.join(SCRATCH, 'sheet_keys.json'), 'w'), indent=0)
    print(f"{len(flat)} files on {(len(flat) + per - 1) // per} sheets")


def session_for(ts, dates):
    """The most recent session played on or before this post (chatter follows the session it is about)."""
    d = ts[:10]
    best = None
    for n, v in sorted(dates.items(), key=lambda kv: int(kv[0])):
        if v['date'] <= d:
            best = int(n)
    return best


def publish():
    items = {i['id']: i for i in json.load(open(os.path.join(SCRATCH, 'discord_index.json'), encoding='utf-8'))}
    review = json.load(open(os.path.join(ROOT, 'content', 'discord_review.json'), encoding='utf-8'))
    dates = json.load(open(os.path.join(ROOT, 'content', 'dates.json'), encoding='utf-8'))
    os.makedirs(OUT_MEDIA, exist_ok=True)
    posts, keep_files = {}, set()
    for key, verdict in review.items():
        if verdict != 'keep' and not (isinstance(verdict, dict) and verdict.get('keep')):
            continue
        mid, j = key.split(':')
        it = items.get(mid)
        if not it:
            continue
        f = it['files'][int(j)]
        stem = f"{mid}_{j}"
        extra = verdict if isinstance(verdict, dict) else {}
        if f['kind'] == 'img':
            src = Image.open(f['path'])
            animated = getattr(src, 'is_animated', False)
            out = os.path.join(OUT_MEDIA, stem + '.webp')
            if not os.path.exists(out):
                if animated:
                    frames = [fr.convert('RGBA').copy() for fr in ImageSequence.Iterator(src)]
                    for fr in frames:
                        fr.thumbnail((720, 720))
                    frames[0].save(out, 'WEBP', save_all=True, append_images=frames[1:], duration=src.info.get('duration', 80), loop=0, quality=70)
                else:
                    im = src.convert('RGB')
                    im.thumbnail((1400, 1400))
                    im.save(out, 'WEBP', quality=80, method=5)
            im = Image.open(out)
            tpath = os.path.join(OUT_MEDIA, stem + '_t.webp')
            if not os.path.exists(tpath):
                t = im.convert('RGB')
                t.thumbnail((480, 480))
                t.save(tpath, 'WEBP', quality=72, method=5)
            media = dict(k='img', src=f'media/discord/{stem}.webp', thumb=f'media/discord/{stem}_t.webp', w=im.width, h=im.height)
            keep_files |= {stem + '.webp', stem + '_t.webp'}
        else:
            out = os.path.join(OUT_MEDIA, stem + '.mp4')
            if not os.path.exists(out):
                shutil.copyfile(f['path'], out)
            poster = os.path.join(OUT_MEDIA, stem + '_p.webp')
            if not os.path.exists(poster):
                import av
                c = av.open(f['path'])
                fr = next(c.decode(video=0)).to_image()
                c.close()
                fr.thumbnail((720, 720))
                fr.save(poster, 'WEBP', quality=72)
            media = dict(k='vid', src=f'media/discord/{stem}.mp4', poster=f'media/discord/{stem}_p.webp', thumb=f'media/discord/{stem}_p.webp')
            keep_files |= {stem + '.mp4', stem + '_p.webp'}
        if extra.get('alt'):
            media['alt'] = extra['alt']
        p = posts.setdefault(mid, dict(id=mid, t=it['t'][:19], a=it['a'], x=extra.get('caption', it['x'])[:400], m=[], s=session_for(it['t'], dates)))
        p['m'].append(media)
    for f in os.listdir(OUT_MEDIA):
        if f not in keep_files:
            os.remove(os.path.join(OUT_MEDIA, f))
    out = sorted(posts.values(), key=lambda p: p['t'])
    json.dump(out, open(os.path.join(ROOT, 'content', 'discord.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    size = sum(os.path.getsize(os.path.join(OUT_MEDIA, f)) for f in os.listdir(OUT_MEDIA)) // (1024 * 1024)
    print(f"{len(out)} posts, {sum(len(p['m']) for p in out)} files, {size} MB")


if __name__ == '__main__':
    {'index': index, 'sheets': sheets, 'publish': publish}[sys.argv[1]]()
