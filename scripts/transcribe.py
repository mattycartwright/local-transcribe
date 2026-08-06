#!/usr/bin/env python3
"""
Local, fast, free transcription for one file. Apple Silicon (MLX / Metal).

Pipeline:
  1. mlx_whisper decodes the audio with ffmpeg and transcribes it on the GPU.
     Only the audio stream is ever decoded, so a 16 GB video costs the same as
     the MP3 inside it.
  2. A post-pass strips the trailing hallucination loop Whisper emits on quiet
     tails, groups segments into paragraphs, and writes:
         Title.md               YAML frontmatter + readable text   <- read this
         Title.srt              captions
         Title.timestamped.txt  [mm:ss] per line
         Title.json             raw Whisper segments (source of truth)

The frontmatter's factual fields are filled here. The judgment fields
(speakers, summary, topics) are left empty for an agent pass. See CLAUDE.md.

For folders / many files use bulk_transcribe.py. For URLs, download first (yt-dlp).

Usage:
    python3 transcribe.py VIDEO_OR_AUDIO --title "Founder Interview" [options]
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")

# A pause this long (seconds) between segments starts a new paragraph...
PARA_GAP = 1.2
# ...and a paragraph is force-broken once it passes this many words.
PARA_MAX_WORDS = 130


def human(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def audio_duration(path):
    """Source duration via ffprobe. Only used for the speed readout."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", path],
            capture_output=True, text=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def transcribe_file(path, model, lang):
    import mlx_whisper  # imported late: the model load is the slow part
    opts = {"path_or_hf_repo": model, "verbose": False}
    if lang:
        opts["language"] = lang
    return mlx_whisper.transcribe(path, **opts)


def norm(text):
    return re.sub(r"[^a-z]", "", text.lower())


def strip_trailing_loop(segments, loop_min=4):
    """Drop a run of identical segments at the very end: Whisper's quiet-tail
    hallucination, where it repeats the last phrase long past where the audio
    actually ended. Only fires at loop_min+ repeats, so real short repeats
    survive. Returns (kept_segments, removed_count)."""
    segs = [s for s in segments if s.get("text", "").strip()]
    if len(segs) < loop_min:
        return segs, 0
    last = norm(segs[-1]["text"])
    if not last:
        return segs, 0
    i = len(segs) - 1
    while i >= 0 and norm(segs[i]["text"]) == last:
        i -= 1
    run = len(segs) - 1 - i
    if run >= loop_min:
        return segs[: i + 1], run
    return segs, 0


def paragraphs(segments):
    """Group segments into readable paragraphs on speech pauses."""
    paras, cur, words, prev_end = [], [], 0, None
    for s in segments:
        text = s["text"].strip()
        if not text:
            continue
        gap = (s["start"] - prev_end) if prev_end is not None else 0
        if cur and (gap >= PARA_GAP or words >= PARA_MAX_WORDS):
            paras.append(" ".join(cur))
            cur, words = [], 0
        cur.append(text)
        words += len(text.split())
        prev_end = s["end"]
    if cur:
        paras.append(" ".join(cur))
    return paras


def ts(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def srt_ts(s):
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int(round((sec % 1) * 1000)):03d}"


def yaml_str(v):
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter(meta):
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(yaml_str(x) for x in v)}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif v is None:
            lines.append(f"{k}:")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {yaml_str(v)}")
    return "\n".join(lines + ["---"])


def write_outputs(segments, out_dir, base, meta, use_frontmatter):
    body = "\n\n".join(paragraphs(segments)).strip()
    meta["words"] = len(body.split())

    md_path = os.path.join(out_dir, f"{base}.md")
    with open(md_path, "w") as f:
        if use_frontmatter:
            f.write(frontmatter(meta) + "\n\n")
            f.write(f"# {meta['title']}\n\n")
        f.write(body + "\n")

    with open(os.path.join(out_dir, f"{base}.timestamped.txt"), "w") as f:
        for s in segments:
            f.write(f"[{ts(s['start'])}] {s['text'].strip()}\n")

    with open(os.path.join(out_dir, f"{base}.srt"), "w") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{srt_ts(s['start'])} --> {srt_ts(s['end'])}\n"
                    f"{s['text'].strip()}\n\n")

    with open(os.path.join(out_dir, f"{base}.json"), "w") as f:
        json.dump({"meta": meta, "segments": segments}, f, indent=1)

    return meta["words"], md_path


def slugify(title):
    return re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-") or "transcript"


def build_meta(src, title, result, model, lang, dur, removed, speakers):
    """Factual fields only. Everything an agent has to judge stays empty."""
    return {
        "title": title,
        "source": os.path.basename(src),
        "source_path": os.path.abspath(src),
        "recorded": dt.datetime.fromtimestamp(os.path.getmtime(src)).date().isoformat(),
        "transcribed": dt.datetime.now().replace(microsecond=0).isoformat(),
        "duration": human(dur),
        "duration_seconds": round(dur, 1),
        "language": result.get("language") or lang or "auto",
        "model": model,
        "words": 0,
        "loop_segments_stripped": removed,
        # --- filled by the agent pass, see CLAUDE.md ---
        "speakers": speakers,
        "summary": None,
        "topics": [],
        "labeled": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="Video or audio file (local path)")
    ap.add_argument("--title", required=True, help="Short title for folder/file names")
    ap.add_argument("--outdir", default=None, help="Where to create the output folder")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    ap.add_argument("--lang", default="en", help='force language ("" = auto-detect)')
    ap.add_argument("--speakers", default="",
                    help='known speakers, e.g. "Ari,Jordan", recorded as a hint')
    ap.add_argument("--no-frontmatter", action="store_true")
    ap.add_argument("--no-clean", action="store_true", help="keep the trailing loop")
    ap.add_argument("--loop-min", type=int, default=4)
    args = ap.parse_args()

    if "://" in args.source:
        print("!! that's a URL. Download it first (yt-dlp), then point this at the "
              "local file.", file=sys.stderr)
        sys.exit(1)
    src = os.path.expanduser(args.source)
    if not os.path.isfile(src):
        print(f"!! not a file: {src}", file=sys.stderr)
        sys.exit(1)

    base = slugify(args.title)
    out_dir = os.path.join(args.outdir or os.path.dirname(os.path.abspath(src)), base)
    os.makedirs(out_dir, exist_ok=True)

    dur = audio_duration(src)
    print(f"{base}  ({human(dur)} audio)  ->  {out_dir}")
    print(f"transcribing on {args.model.split('/')[-1]}...")

    t0 = time.monotonic()
    result = transcribe_file(src, args.model, args.lang)
    wall = time.monotonic() - t0

    segments = result.get("segments", [])
    if args.no_clean:
        segments = [s for s in segments if s.get("text", "").strip()]
        removed = 0
    else:
        segments, removed = strip_trailing_loop(segments, args.loop_min)

    speakers = [s.strip() for s in args.speakers.split(",") if s.strip()]
    meta = build_meta(src, args.title, result, args.model, args.lang, dur,
                      removed, speakers)
    words, md_path = write_outputs(segments, out_dir, base, meta,
                                   not args.no_frontmatter)

    print("=" * 52)
    print(f"Done in {human(wall)}  ({(dur / wall if wall else 0):.1f}x real-time)"
          f"  |  {words} words")
    if removed:
        print(f"Stripped {removed} trailing hallucination-loop segments.")
    print(f"Read this: {md_path}")


if __name__ == "__main__":
    main()
