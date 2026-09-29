"""Cut a 720p video clip and a poster frame for every moment in content/moments.json.

Needs an ffmpeg binary: `pip install imageio-ffmpeg` (or set FFMPEG=path\to\ffmpeg.exe).
Usage:  python tools/videoclips.py            (only clips that are missing or whose timing changed)
        python tools/videoclips.py --force    (re-cut everything)

Clips go to docs/media/video/<moment-id>.mp4 with docs/media/video/<moment-id>.webp posters.
"""
import concurrent.futures as cf, glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(os.path.dirname(ROOT), 'Session recordings')
OUT = os.path.join(ROOT, 'docs', 'media', 'video')
STATE = os.path.join(OUT, 'cuts.json')          # moment id -> "t+d" it was cut with


def ffmpeg():
    if os.environ.get('FFMPEG'):
        return os.environ['FFMPEG']
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def recording(n):
    for pat in (f"Session {n} *", f"Session {n}-*", f"Session {n}.*"):
        fs = [f for f in glob.glob(os.path.join(REC, pat)) if f.lower().endswith(('.mp4', '.mkv'))]
        if fs:
            return fs[0]


def cut(ff, m, src):
    mp4 = os.path.join(OUT, f"{m['id']}.mp4")
    tmp = mp4 + '.part.mp4'
    fade = max(0.0, m['d'] - 0.6)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', str(m['t']), '-i', src, '-t', str(m['d']),
                    '-vf', f"scale=1280:720:flags=lanczos,fps=24,fade=t=in:st=0:d=0.3,fade=t=out:st={fade}:d=0.6",
                    '-af', f"afade=t=in:st=0:d=0.3,afade=t=out:st={fade}:d=0.6,loudnorm=I=-18:TP=-2:LRA=11",
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '32', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '80k', '-ac', '2', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, mp4)
    # poster: a frame a third of the way in, where the scene is usually set up
    subprocess.run([ff, '-y', '-loglevel', 'error', '-ss', str(round(m['d'] / 3, 1)), '-i', mp4, '-frames:v', '1',
                    '-vf', 'scale=640:-2', '-c:v', 'libwebp', '-quality', '72', os.path.join(OUT, f"{m['id']}.webp")], check=True)
    return m['id'], os.path.getsize(mp4)


def main():
    force = '--force' in sys.argv
    ff = ffmpeg()
    os.makedirs(OUT, exist_ok=True)
    moments = json.load(open(os.path.join(ROOT, 'content', 'moments.json'), encoding='utf-8'))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    todo = []
    for m in moments:
        key = f"{m['t']}+{m['d']}"
        if not force and state.get(m['id']) == key and os.path.exists(os.path.join(OUT, f"{m['id']}.mp4")):
            continue
        src = recording(m['s'])
        if not src:
            print('no recording for session', m['s'], m['id'])
            continue
        todo.append((m, src, key))
    with cf.ThreadPoolExecutor(int(os.environ.get('JOBS', 4))) as ex:
        futs = {ex.submit(cut, ff, m, src): (m, key) for m, src, key in todo}
        for f in cf.as_completed(futs):
            m, key = futs[f]
            try:
                mid, size = f.result()
                state[mid] = key
                print('cut', mid, f'{size // 1024} KB', flush=True)
            except subprocess.CalledProcessError as e:
                print('FAILED', m['id'], e, flush=True)
            json.dump(state, open(STATE, 'w'), indent=0)
    keep = {m['id'] for m in moments}
    for f in os.listdir(OUT):
        stem = f.split('.')[0]
        if f.endswith(('.mp4', '.webp')) and stem not in keep:
            os.remove(os.path.join(OUT, f))
            print('removed old', f)
    state = {k: v for k, v in state.items() if k in keep}
    json.dump(state, open(STATE, 'w'), indent=0)
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) // (1024 * 1024)
    print(f'{len(todo)} cut, {len(state)} clips, {total} MB')


if __name__ == '__main__':
    main()
