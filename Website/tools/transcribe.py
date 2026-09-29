"""Transcribe every moment's audio clip into content/transcripts.json.

Needs faster-whisper:  pip install faster-whisper
Usage:  python tools/transcribe.py              (only clips without a transcript, or re-cut since)
        python tools/transcribe.py --force      (transcribe everything again)
        python tools/transcribe.py --model small.en   (faster, less accurate; default large-v3-turbo)

The transcripts are raw machine output with no speaker labels. They feed moment tagging
(content/moments.json `pcs`, `kind`, `lines`, `quote`) and site search; they are not shown verbatim.
"""
import argparse, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'content', 'transcripts.json')
# names Whisper would otherwise mishear
PROMPT = ("A Dungeons and Dragons session. Ulrick, Durzo, Gideon, Fiddle, D.E.R.E.K., B0B, Nate, Lyrial, Gavin, "
          "Borak, Elara, Nyxara, Agni, Auril, Gaia, Chronos, Blibdoolpoolp, Muttonham, Nogratis, Fireholm, Skycrest, modrons.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--model', default='large-v3-turbo')
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device='cpu', compute_type='int8')
    moments = json.load(open(os.path.join(ROOT, 'content', 'moments.json'), encoding='utf-8'))
    done = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    n = 0
    for m in moments:
        src = os.path.join(ROOT, 'docs', m.get('audio') or f"media/audio/{m['id']}.m4a")
        if not os.path.exists(src):
            continue
        if not args.force and done.get(m['id'], {}).get('cut') == m.get('cut'):
            continue
        segs, _ = model.transcribe(src, language='en', beam_size=5, initial_prompt=PROMPT, vad_filter=True,
                                   condition_on_previous_text=False)
        out = []
        for s in segs:
            text = s.text.strip()
            if out and out[-1][2] == text:   # Whisper sometimes loops on one line
                continue
            out.append([round(s.start, 1), round(s.end, 1), text])
        done[m['id']] = dict(cut=m.get('cut'), model=args.model, segs=out)
        n += 1
        print('transcribed', m['id'], flush=True)
        json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    keep = {m['id'] for m in moments}
    done = {k: v for k, v in sorted(done.items()) if k in keep}
    json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{n} transcribed, {len(done)} transcripts')


if __name__ == '__main__':
    main()
