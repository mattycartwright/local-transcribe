# local-transcribe

Whisper on the Mac GPU, wrapped in ~370 lines of Python so the output is usable. No API key, no upload, no cap. I got tired of paying by the minute to transcribe my own voice memos.

```bash
brew install ffmpeg && pip3 install mlx-whisper
python3 scripts/transcribe.py talk.mov --title "Talk"
```

Out comes a folder: `.md` (YAML frontmatter, paragraphs broken on real pauses in the speech), `.srt`, `.timestamped.txt`, and `.json` with the raw segments, which is the source of truth.

M4 Pro, `large-v3-turbo`: 23 min of clean audio in 40s (34x). A messy 43-min two-person interview in ~3 min (~14x). Model is 1.5GB, downloads once, then nothing touches the network. Run with `HF_HUB_OFFLINE=1` if you want proof.

`bulk_transcribe.py` takes files or folders and keeps the model resident across the batch. That's the only reason it exists. Don't loop the single-file script in bash, that's a model load per file.

Two things that cost me an afternoon:

1. **Whisper hallucinates on quiet tails.** It repeats the last phrase over and over, well past where the audio ended. `strip_trailing_loop()` drops a run of 4+ identical final segments and records the count in the frontmatter. If a transcript ends in a repeat, check the `.json` for the true end.
2. **The `mlx_whisper` CLI honors only the last `--output-format` you pass**, silently. I use the Python API and derive every format from the segments.

### CLAUDE.md

Whisper doesn't diarize. There's no flag for it. But for two or three speakers you don't need a second model, you need to read the timestamped file and assign turns from content: who asks vs. who answers, who says "when I started the company," who gets named in a greeting. That's an LLM pass, so [CLAUDE.md](CLAUDE.md) is that pass written down. It fixes which frontmatter fields the script owns vs. the agent, the labeled output format, and a confirm-list convention for proper nouns, because Whisper renders names phonetically and a wrong name in a published quote is a real problem.

It's a prompt in a file, versioned next to the code it drives. Point Claude Code at the repo and say "transcribe this, then label the speakers." Steal the file and change the schema to whatever you actually track. That's the part worth copying.

### Notes

- `--lang en` is the default. Auto-detect occasionally reads a quiet intro as Welsh.
- Only the audio stream is decoded, so a 16GB video costs what the MP3 inside it costs. No size limit.
- MLX is Metal-only. Swap `transcribe_file()` for faster-whisper or whisper.cpp anywhere else. Same segment shape, nothing downstream changes.
- `--model` takes any `mlx-community` Whisper repo. `large-v3-turbo` is the default and I've never had a reason to change it.

MIT.
