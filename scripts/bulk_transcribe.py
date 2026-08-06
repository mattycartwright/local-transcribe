#!/usr/bin/env python3
"""
Bulk transcription: files and folders, one model load for the whole batch.

Same pipeline and same outputs as transcribe.py, but the model stays resident
between files, so a batch of 50 short clips pays the ~10 s model load once
instead of 50 times.

Usage:
    python3 bulk_transcribe.py PATH [PATH ...] [--out DIR] [--flat] [--skip-existing]

PATH is a file or a folder (folders are walked recursively for common video and
audio extensions). By default each source gets its own output folder named after
the file; --flat writes everything into --out directly.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcribe import (  # noqa: E402  (same-dir sibling, not a package)
    DEFAULT_MODEL, audio_duration, build_meta, human, slugify,
    strip_trailing_loop, transcribe_file, write_outputs,
)

VIDEO_AUDIO_EXTS = {
    ".mov", ".mp4", ".m4v", ".mkv", ".webm", ".avi", ".mpg", ".mpeg",
    ".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus", ".aiff", ".caf",
}


def collect_inputs(paths):
    files = []
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in names:
                    if n.startswith("."):
                        continue
                    if os.path.splitext(n)[1].lower() in VIDEO_AUDIO_EXTS:
                        files.append(os.path.join(root, n))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"!! skip (not found): {p}", file=sys.stderr)
    return sorted(set(files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="video/audio files or folders")
    ap.add_argument("--out", default=None, help="output root (default: next to each source)")
    ap.add_argument("--flat", action="store_true", help="no per-file subfolder")
    ap.add_argument("--skip-existing", action="store_true", help="skip if the .md exists")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--lang", default="en", help='force language ("" = auto-detect)')
    ap.add_argument("--no-frontmatter", action="store_true")
    ap.add_argument("--loop-min", type=int, default=4)
    args = ap.parse_args()

    files = collect_inputs(args.paths)
    if not files:
        print("No video/audio files found.", file=sys.stderr)
        sys.exit(1)

    print(f"{len(files)} file(s)  |  model: {args.model.split('/')[-1]}\n")
    total_audio = total_wall = 0.0
    done = failed = skipped = 0

    for i, src in enumerate(files, 1):
        title = os.path.splitext(os.path.basename(src))[0]
        base = slugify(title)
        root = args.out or os.path.dirname(os.path.abspath(src))
        out_dir = root if args.flat else os.path.join(root, base)
        md_path = os.path.join(out_dir, f"{base}.md")

        if args.skip_existing and os.path.exists(md_path):
            print(f"[{i}/{len(files)}] {base}  (skipped, exists)")
            skipped += 1
            continue

        os.makedirs(out_dir, exist_ok=True)
        dur = audio_duration(src)
        total_audio += dur
        print(f"[{i}/{len(files)}] {base}  ({human(dur)})")

        t0 = time.monotonic()
        try:
            result = transcribe_file(src, args.model, args.lang)
        except Exception as e:  # a corrupt file shouldn't kill a 200-file batch
            print(f"  !! failed: {e}\n", file=sys.stderr)
            failed += 1
            continue
        wall = time.monotonic() - t0
        total_wall += wall

        segments, removed = strip_trailing_loop(result.get("segments", []), args.loop_min)
        meta = build_meta(src, title, result, args.model, args.lang, dur, removed, [])
        words, _ = write_outputs(segments, out_dir, base, meta, not args.no_frontmatter)
        done += 1
        print(f"  {human(wall)}  ({(dur / wall if wall else 0):.1f}x)  "
              f"{words} words  -> {out_dir}\n")

    print("=" * 52)
    print(f"Transcribed {done}/{len(files)}"
          f"{f'  (skipped {skipped})' if skipped else ''}"
          f"{f'  (failed {failed})' if failed else ''}")
    print(f"Audio: {human(total_audio)}   Compute: {human(total_wall)}")
    if total_wall:
        print(f"Overall: {total_audio / total_wall:.1f}x real-time")


if __name__ == "__main__":
    main()
