# local-transcribe

Whisper transcription that runs entirely on your Mac. No API key, no upload, no per-minute billing. Roughly 15-35x real-time on Apple Silicon, and the output is a clean Markdown file with YAML frontmatter instead of a wall of text.

A 23-minute recording finishes in 40 seconds. A 43-minute interview in about 3 minutes. Cost: $0, every time.

```bash
python3 scripts/transcribe.py interview.mov --title "Founder Interview"
```

```
Founder-Interview/
├── Founder-Interview.md               <- frontmatter + readable paragraphs
├── Founder-Interview.srt              <- captions
├── Founder-Interview.timestamped.txt  <- [mm:ss] per line
└── Founder-Interview.json             <- raw Whisper segments
```

---

## Why bother when the API exists

| | Whisper API | local-transcribe |
|---|---|---|
| 100 hours of audio | ~$36 | $0 |
| Your audio leaves the machine | yes | no |
| Max file size | 25 MB | none (a 16 GB video is fine) |
| Works on a plane | no | yes |
| Speed | network-bound | 15-35x real-time |

The 25 MB cap is the one that bites. A one-hour interview off a phone blows past it, so you end up writing a chunker. Here only the audio stream is ever decoded, so the size of the video is irrelevant.

## Requirements

- Apple Silicon Mac (M1 or newer). MLX is Metal-only. On Intel or Linux see [Not on Apple Silicon](#not-on-apple-silicon).
- Python 3.9+
- ffmpeg

## Install

```bash
brew install ffmpeg
pip3 install mlx-whisper
git clone https://github.com/mattycartwright/local-transcribe.git
```

That's it. The model (1.5 GB) downloads itself on the first run and is cached in `~/.cache/huggingface` forever after.

## Use it

**One file:**

```bash
python3 scripts/transcribe.py ~/Movies/interview.mov --title "Founder Interview"
```

**A whole folder.** The model loads once for the entire batch, not once per file:

```bash
python3 scripts/bulk_transcribe.py ~/Movies/raw-footage --out ~/transcripts --skip-existing
```

**A URL.** Download it first, then point at the local file:

```bash
yt-dlp -f "bv*+ba/b" "https://youtube.com/watch?v=..." -o talk.mp4
python3 scripts/transcribe.py talk.mp4 --title "The Talk"
```

## What the output looks like

`Founder-Interview.md`:

```markdown
---
title: "Founder Interview"
source: "IMG_4471.MOV"
source_path: "/Users/you/Movies/IMG_4471.MOV"
recorded: "2026-08-02"
transcribed: "2026-08-05T22:03:04"
duration: "43:12"
duration_seconds: 2592.4
language: "en"
model: "mlx-community/whisper-large-v3-turbo"
words: 7412
loop_segments_stripped: 6
speakers: ["Ari", "Jordan"]
summary:
topics: []
labeled: false
---

# Founder Interview

So the thing nobody tells you about starting a company is that the first
year is mostly admin...
```

Every field down to `loop_segments_stripped` is a fact the script already knows: duration, model, word count, file dates. `summary`, `topics` and `labeled` are deliberately left empty. That's the handoff point.

## The agent layer: speaker names, summaries, real frontmatter

Whisper does not do speaker diarization. It hands back one undifferentiated stream of text, which is close to useless for interviews and podcasts.

The fix is a second pass by an LLM that reads the timestamped output and assigns speakers **from content**: who asks versus who answers, who says "when I started my company," who gets named in a greeting. It fills the empty frontmatter fields on the same pass.

[**CLAUDE.md**](CLAUDE.md) is that second pass, written as instructions. Open this repo in [Claude Code](https://claude.com/claude-code) and say:

```
transcribe ~/Movies/interview.mov, then label the speakers
```

and you get `Founder-Interview.labeled.md`:

```markdown
---
title: "Founder Interview"
speakers: ["Ari Nakamura", "Jordan Reyes"]
summary: "Jordan walks through why the company started as a marketplace
  and what broke when they tried to sell direct."
topics: ["marketplaces", "founder story", "pricing"]
labeled: true
...
---

**ARI:** Take me back to the beginning. What was the first version?

**JORDAN:** The first version was a spreadsheet, honestly...
```

CLAUDE.md covers the frontmatter contract, the speaker-labeling format, the confirm-list convention for proper nouns Whisper mangles, and the rules an agent may never break. It works with any agent that reads a project instruction file (Claude Code, Cursor, Codex), and it reads fine as a plain checklist if you'd rather do the pass yourself.

## Options

```
transcribe.py SOURCE --title NAME
  --outdir DIR        where to create the output folder (default: next to source)
  --model NAME        any mlx-community Whisper repo (default: large-v3-turbo)
  --lang CODE         force a language; "" to auto-detect (default: en)
  --speakers "A,B"    known speaker names, recorded in frontmatter as a hint
  --no-frontmatter    plain text output
  --no-clean          keep Whisper's trailing hallucination loop
  --loop-min N        how many identical tail segments count as a loop (default 4)

bulk_transcribe.py PATH [PATH ...]
  --out DIR           output root
  --flat              no per-file subfolder
  --skip-existing     skip anything already transcribed
  (plus --model, --lang, --no-frontmatter, --loop-min)
```

Set a default model without typing it every time: `export WHISPER_MODEL=mlx-community/whisper-medium-mlx`.

## Models

| Repo | Disk | Notes |
|---|---|---|
| `mlx-community/whisper-large-v3-turbo` | 1.5 GB | **Default.** Best speed-to-accuracy trade by a distance |
| `mlx-community/whisper-large-v3-mlx` | ~3 GB | Slower, marginally better on hard audio and non-English |
| `mlx-community/whisper-medium-mlx` | ~1.5 GB | No real reason to prefer this over turbo |
| `mlx-community/whisper-small-mlx` | ~0.5 GB | Fine for clean English, noticeably worse on names |
| `mlx-community/whisper-base-mlx` | ~0.15 GB | Rough drafts and keyword spotting only |

## Speed

Measured on an M4 Pro (48 GB), macOS 26.5, mlx-whisper 0.4.3, `large-v3-turbo`:

| Audio | Wall clock | Rate |
|---|---|---|
| 23 min, clean studio-style speech | 40 s | 34x |
| 43 min, real two-person interview | ~3 min | ~14x |
| 19 s clip, cold start with model load | 2 s | 7x |

Clean audio runs at the top of that range. Messy rooms, crosstalk and heavy accents pull it down. Either way it's minutes, not an afternoon, and the GPU does the work while you keep using the machine.

## How it works

```
source file  --ffmpeg-->  16 kHz mono audio  --MLX/Metal-->  Whisper segments
                                                                    |
                                        strip trailing loop <-------+
                                                |
                        paragraph grouping on pauses >1.2s
                                                |
                                  .md + .srt + .timestamped.txt + .json
                                                |
                              (optional) agent pass --> .labeled.md
```

ffmpeg is invoked by mlx-whisper itself, so there's no scratch WAV left behind to clean up.

## Gotchas

These cost real time to discover:

- **Whisper hallucinates loops on quiet tails.** On trailing silence it repeats the last phrase dozens of times past where the audio actually ended: *"...what are you interested, what are you interested, what are you interested..."*. `transcribe.py` strips a run of 4+ identical final segments and records the count in `loop_segments_stripped`. If a transcript ends in an obvious repeat, that's this, and the raw `.json` has the true end. `--no-clean` disables it.
- **The mlx_whisper CLI honors only one `--output-format`.** Passing it repeatedly silently keeps the last one. These scripts use the Python API and derive every format from the segments, so it doesn't bite here. It will if you script the CLI yourself.
- **Never hand Whisper the video.** It only wants 16 kHz mono. Both scripts already do this. The point is that the file size in your Finder window is not the file size Whisper sees.
- **Proper nouns are the weak spot.** Names, brands and jargon come back phonetically ("Kelemen" turns into "Kelliman"). That's what the confirm-list convention in CLAUDE.md is for. Don't let an agent silently "fix" them either.
- **The first run downloads 1.5 GB.** It looks like a hang. It isn't.

## Not on Apple Silicon

MLX is Metal-only. Everything else here (the loop stripping, paragraph grouping, frontmatter contract, CLAUDE.md agent layer) is portable. Swap the engine in `transcribe_file()` for one of:

- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), CTranslate2 under the hood, excellent on NVIDIA and respectable on CPU
- [`whisper.cpp`](https://github.com/ggerganov/whisper.cpp), runs anywhere, including a Raspberry Pi if you're patient

Both return the same segment shape (`start`, `end`, `text`), so nothing downstream changes.

## License

MIT. See [LICENSE](LICENSE).
