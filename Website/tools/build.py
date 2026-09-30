"""Build the War of the Gods site: content/*.json + content/pages/*.html -> docs/index.html + docs/data/site.json.

Run from anywhere:  python tools/build.py
"""
import argparse, json, os, re, datetime
from art_site import attach_art

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = lambda *p: os.path.join(ROOT, 'content', *p)
D = lambda *p: os.path.join(ROOT, 'docs', *p)


def load(name, default=None):
    p = C(name)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding='utf-8'))


MONTHS = [("Stormcrown", 1), ("Wolfmoon", 31), ("Frostfall", 61), ("Longnight", 91), ("Midwinter", 121)]


def reckon(daystr):
    m = re.match(r'(\d+)', daystr)
    if not m:
        return ""
    d = int(m.group(1))
    name, start = [x for x in MONTHS if x[1] <= d][-1]
    n = d - start + 1
    suf = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suf} of {name}"


def expand(ranges):
    out = {}
    for k, v in ranges.items():
        a, _, b = k.partition('-')
        for n in range(int(a), int(b or a) + 1):
            out[n] = v
    return out


def hero_arcs(heroes, sessions):
    """For each hero, the sentences of every session summary that mention them: their story in the table's own words."""
    for h in heroes:
        pat = re.compile(r'(?<![\w.])(?:' + '|'.join(re.escape(x) for x in h['match']) + r')(?![\w])')
        arc = []
        for s in sessions:
            # keep dotted names (D.E.R.E.K., B.0.B.) whole while splitting into sentences
            text = re.sub(r'(?:[A-Z0-9]\.){2,}', lambda m: m.group().replace('.', '\u2024'), s['text'])
            said = [x.replace('\u2024', '.') for x in re.split(r'(?<=[.!?])\s+(?=[A-Z"<])', text)]
            said = [x for x in said if pat.search(re.sub(r'<[^>]+>', '', x))]
            if said:
                arc.append(dict(n=s['n'], x=' '.join(said)))
        h['arc'] = arc
    return heroes


def main(output_dir=None):
    destination = os.path.abspath(output_dir or D())
    out = lambda *p: os.path.join(destination, *p)
    sess = load('sessions.json')
    videos = load('videos.json')
    media = load('media_index.json')
    locs = load('locations.json')
    moments = load('moments.json', [])
    moments = attach_art(moments, ROOT, destination)
    posts = load('discord.json', [])
    dates = load('dates.json', {})
    loc_of = expand(locs['session_locations'])

    sessions, chapters = [], []
    for c in sess['chapters']:
        chapters.append(dict(num=c['num'], title=c['title'], place=c['place'], blurb=c['blurb'], sessions=[s['n'] for s in c['sessions']]))
        for s in c['sessions']:
            n = s['n']
            gods, plain, cats = [], [], set()
            for t in s.get('tags', []):
                if t.startswith('god:'):
                    gods.append(t[4:]); cats.add('gods')
                elif t in ('battle', 'prophecy', 'modrons'):
                    cats.add({'battle': 'battles'}.get(t, t)); plain.append({'battle': 'Battle', 'prophecy': 'Prophecy', 'modrons': 'Modrons'}[t])
                elif t == 'death':
                    cats.add('deaths')
                else:
                    plain.append(t)
            if s.get('dead'):
                cats.add('deaths')
            if any(m['s'] == n for m in moments):
                cats.add('fun')
            nums = [int(x) for x in re.findall(r'\d+', s['day'])]
            v = videos['sessions'].get(str(n))
            dt = dates.get(str(n), {})
            sessions.append(dict(
                n=n, title=s['title'], day=s['day'], reckoned=reckon(s['day']), dayLo=nums[0], dayHi=nums[-1] if len(nums) > 1 and nums[-1] < 200 else nums[0],
                text=s['text'], gods=gods, plain=plain, dead=s.get('dead', []), cats=sorted(cats),
                clips=[dict(id=k, title=videos['clips'].get(k, {}).get('title', 'Clip')) for k in s.get('clips', [])],
                sumt=s.get('sumt', 0), video=v, thumb=media['thumbs'].get(str(n)) or (media['thumbs'].get('Recap') if n <= 13 else None),
                loc=loc_of.get(n), real=dt.get('date'), realApprox=dt.get('approx', True)))

    last = max(s['n'] for s in sessions)
    heroes = hero_arcs(load('heroes.json', []), sessions)
    known = {h['id'] for h in heroes}
    # video clips cut by tools/videoclips.py; VIDEO_BASE can point them at another host (see content/site_config.json)
    vbase = os.environ.get('VIDEO_BASE') or load('site_config.json', {}).get('video_base', 'media/video/')
    for m in moments:
        bad = [p for p in m.get('pcs', []) if p not in known]
        if bad:
            raise SystemExit(f"moment {m['id']}: unknown hero id(s) {bad} (see content/heroes.json)")
        # the poster marks a finished cut; the .mp4 sits beside it unless video_base says otherwise
        if os.path.exists(D('media', 'video', f"{m['id']}.webp")):
            m['video'] = f"{vbase}{m['id']}.mp4"
            m['poster'] = f"media/video/{m['id']}.webp"
    # the campaign trailer plays from the home page once docs/media/video/trailer.mp4 is in place
    trailer = None
    if os.path.exists(D('media', 'video', 'trailer.mp4')):
        trailer = dict(src=f"{vbase}trailer.mp4")
        if os.path.exists(D('media', 'video', 'trailer.webp')):
            trailer['poster'] = 'media/video/trailer.webp'
    site = dict(
        stats=dict(days=max(s['dayHi'] for s in sessions)), trailer=trailer,
        chapters=chapters, sessions=sessions, locations=locs['locations'], map=locs['map'],
        moments=moments, posts=posts, videos=videos, heroes=heroes,
        built=datetime.date.today().isoformat())
    os.makedirs(out('data'), exist_ok=True)
    json.dump(site, open(out('data', 'site.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    html = open(C('template.html'), encoding='utf-8').read()
    for name in ('fallen', 'heroes', 'gods', 'people'):
        html = html.replace(f'<!--PAGE:{name}-->', open(C('pages', f'{name}.html'), encoding='utf-8').read())
    ver = datetime.datetime.now().strftime('%Y%m%d%H%M')
    html = html.replace('__V__', ver).replace('__LAST__', str(last)).replace('__DATE__', datetime.date.today().strftime('%d %B %Y').lstrip('0'))
    open(out('index.html'), 'w', encoding='utf-8').write(html)
    # keep search engines out: this is a site for the table, not the internet
    open(out('robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    open(out('.nojekyll'), 'w').write('')
    kb = os.path.getsize(out('data', 'site.json')) // 1024
    art_count = sum(bool(m.get('art')) for m in moments)
    print(f"built: {len(sessions)} sessions, {len(moments)} moments, {len(posts)} posts, {art_count} artworks, site.json {kb} KB")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', help='Write generated build files to this directory instead of docs/ (assets are not copied).')
    main(parser.parse_args().output_dir)
