"""Cut an audio clip for every moment in content/moments.json from the local session recordings.

Needs PyAV and numpy:  pip install av numpy
Usage:  python tools/clips.py            (only clips that don't exist yet)
        python tools/clips.py --force    (re-cut everything)
"""
import av, glob, json, os, sys, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(os.path.dirname(ROOT), 'Session recordings')
OUT = os.path.join(ROOT, 'docs', 'media', 'audio')
SR = 44100
FADE = 0.25


def recording(n):
    for pat in (f"Session {n} *", f"Session {n}-*", f"Session {n}.*"):
        fs = [f for f in glob.glob(os.path.join(REC, pat)) if f.lower().endswith(('.mp4', '.mkv'))]
        if fs:
            return fs[0]


def decode(path, start, dur):
    c = av.open(path)
    s = c.streams.audio[0]
    c.seek(int(max(0, start - 3) * av.time_base), any_frame=False)
    rs = av.AudioResampler(format='flt', layout='mono', rate=SR)
    buf, t0 = [], None
    for fr in c.decode(s):
        if fr.time is None:
            continue
        for f in rs.resample(fr):
            if t0 is None:
                t0 = fr.time
            buf.append(f.to_ndarray().reshape(-1))
        if fr.time > start + dur + 1:
            break
    c.close()
    x = np.concatenate(buf)
    i = int(round((start - t0) * SR))
    return x[max(0, i): max(0, i) + int(dur * SR)]


def encode(x, out):
    # gentle loudness levelling so every clip plays at a similar volume
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * min(8.0, 0.1 / rms)
    x = np.tanh(x * 1.2) / np.tanh(1.2)
    n = int(FADE * SR)
    ramp = np.linspace(0, 1, n, dtype=np.float32)
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    c = av.open(out, 'w', format='mp4')
    st = c.add_stream('aac', rate=SR)
    st.layout = 'mono'
    st.bit_rate = 56000
    step = 1024
    for i in range(0, len(x), step):
        fr = av.AudioFrame.from_ndarray(x[i:i + step].astype(np.float32).reshape(1, -1), format='flt', layout='mono')
        fr.sample_rate = SR
        for p in st.encode(fr):
            c.mux(p)
    for p in st.encode(None):
        c.mux(p)
    c.close()


def main():
    force = '--force' in sys.argv
    moments = json.load(open(os.path.join(ROOT, 'content', 'moments.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    done = 0
    for m in moments:
        out = os.path.join(OUT, f"{m['id']}.m4a")
        m['audio'] = f"media/audio/{m['id']}.m4a"
        key = f"{m['t']}+{m['d']}"
        if os.path.exists(out) and m.get('cut') == key and not force:
            continue
        path = recording(m['s'])
        if not path:
            print('no recording for session', m['s'])
            m.pop('audio')
            continue
        encode(decode(path, m['t'], m['d']), out)
        m['cut'] = key
        done += 1
        print('cut', m['id'], f"{os.path.getsize(out) // 1024} KB")
    keep = {f"{m['id']}.m4a" for m in moments}
    for f in os.listdir(OUT):
        if f.endswith('.m4a') and f not in keep:
            os.remove(os.path.join(OUT, f)); print('removed old clip', f)
    json.dump(moments, open(os.path.join(ROOT, 'content', 'moments.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{done} clips cut, {len(moments)} moments')


if __name__ == '__main__':
    main()
