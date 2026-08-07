# local-transcribe

**Stop paying a subscription to transcribe your own audio.**

Whisper runs on the GPU in your Mac. This repo turns that into a real workflow: point it at any file with a voice in it and get back clean Markdown with YAML frontmatter, captions, and timestamps. No account, no upload, no per-minute meter, no monthly fee, no cap on how much you run through it.

A 23-minute recording finishes in 40 seconds. A 43-minute interview in about 3 minutes. A folder of 300 clips while you sleep.

```bash
python3 scripts/transcribe.py anything.mov --title "Whatever This Is"
```

```
Whatever-This-Is/
├── Whatever-This-Is.md               <- frontmatter + readable paragraphs
├── Whatever-This-Is.srt              <- captions
├── Whatever-This-Is.timestamped.txt  <- [mm:ss] per line
└── Whatever-This-Is.json             <- raw Whisper segments
```

---

## What you're paying for this right now

Transcribing 20 hours a month, which is one podcast a week plus your meetings:

| Service | Plan | Per year |
|---|---|---|
| Rev | pay-as-you-go AI, $0.25/min | **$3,600** |
| Sonix | pay-as-you-go, $10/hr | **$2,400** |
| Sonix | Advanced, $50/mo, 20 hrs included | **$600** |
| Descript | Creator, $24/mo annual, 30 hrs included | **$288** |
| Otter | Business, $19.99/seat/mo annual | **$240** |
| Fireflies | Business, $19/seat/mo annual | **$228** |
| Otter | Pro, $8.33/mo annual, 20 hrs included (exactly at the cap) | **$100** |
| OpenAI Whisper API | $0.006/min | **$86** |
| **local-transcribe** | there is no plan | **$0** |

List prices as of August 2026, annual billing where it's cheaper. Rev's human transcription is $1.99/min, which is $2,388 for those same 20 hours in a single month. Different product, worth knowing.

**The money is not really the point.** The cap is. Every row above has a meter running, so you start rationing: is this call worth 40 of my 1,200 minutes? You end up transcribing the important stuff and losing everything else. Take the meter away and the behavior changes. You transcribe every voice memo, every call, and the four years of recordings sitting in a folder you've never opened.

## Point it at anything with a voice in it

The same command handles all of these. Nothing here is a separate product tier.

**Creators.** Podcast episodes into show notes, chapters and timestamps. YouTube videos into SRT captions and a first-draft blog post. Reels and TikToks into a searchable archive of your own hooks, so you can find the line that worked eight months ago.

**Meetings and calls.** Client calls, standups, 1:1s, board meetings, sales calls, contractor check-ins. Anything you recorded and were going to "write up later."

**Interviews.** Journalism, user research, customer discovery, hiring debriefs, oral history. The agent layer below turns these into speaker-labeled transcripts, which is the part that actually takes a human an hour per hour of tape.

**Study and research.** Lectures, seminars, conference talks, qualitative research you need to code, a language class you want to read back.

**Your own voice.** Voice memos, walking notes, the idea you talked into your phone in the car. This is the use that gets rationed hardest under a subscription, and it's the one with the best return.

**Archives.** Point `bulk_transcribe.py` at a folder of 300 files and go to bed. Old family tapes, digitized VHS, years of unlabeled recordings. It costs a night of GPU time and nothing else.

**Accessibility.** Real SRT captions for anything you publish, at whatever volume you publish.

## The recordings you can't upload

Every service in that table works by sending your audio to someone else's servers. For a lot of recordings that's a non-starter: client calls under NDA, HR conversations, legal matters, medical and therapy sessions, unreleased product, an interview where a source's safety depends on it, anything involving a minor.

This one has no network in the transcription path. Once the model is cached, nothing calls out. Prove it to yourself:

```bash
HF_HUB_OFFLINE=1 python3 scripts/transcribe.py sensitive.mov --title "Session 12"
```

That runs on a plane, in a SCIF, in a field site with no signal, and on a laptop that has never been given an API key.

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

That's the whole setup. The model (1.5 GB) downloads itself on the first run and is cached in `~/.cache/huggingface` forever after.

## Use it

**One file:**

```bash
python3 scripts/transcribe.py ~/Movies/interview.mov --title "Founder Interview"
```

**A whole folder.** The model loads once for the entire batch, not once per file, which is the difference between a long night and a short one:

```bash
python3 scripts/bulk_transcribe.py ~/Movies/raw-footage --out ~/transcripts --skip-existing
```

**A URL.** Download it first, then point at the local file:

```bash
yt-dlp -f "bv*+ba/b" "https://youtube.com/watch?v=..." -o talk.mp4
python3 scripts/transcribe.py talk.mp4 --title "The Talk"
```

**Voice memos off your phone.** AirDrop the folder, then:

```bash
python3 scripts/bulk_transcribe.py ~/Downloads/voice-memos --out ~/notes --flat
```

## What the output looks like

Not a wall of text. `Founder-Interview.md`:

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

Paragraphs break on real pauses in the speech, so it reads like a document instead of a transcript dump. Every field down to `loop_segments_stripped` is a fact the script already knows. `summary`, `topics` and `labeled` are deliberately left empty. That's the handoff point.

Drop the `.md` straight into Obsidian, a Jekyll or Astro site, or anything else that reads frontmatter, and it's already indexed.

## The agent layer: speaker names, summaries, real metadata

Whisper does not do speaker diarization. It hands back one undifferentiated stream of text, which is close to useless for an interview, a podcast, or a four-person meeting. This is the single biggest reason people keep paying for Otter and Descript.

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
confirm: ["Kelemen", "Northwind Supply"]
---

**ARI:** Take me back to the beginning. What was the first version?

**JORDAN:** The first version was a spreadsheet, honestly...
```

CLAUDE.md defines the frontmatter contract (which fields the script owns and which the agent owns), the speaker-labeling format, the confirm-list convention for proper nouns Whisper mangles, and the rules an agent may never break: never invent, never overwrite the source of truth, never silently fix a fact the speaker got wrong.

It works with any agent that reads a project instruction file (Claude Code, Cursor, Codex), and it reads fine as a plain checklist if you'd rather do the pass by hand. It's also the part to steal and adapt. Add `client`, `project`, `billable_minutes`, whatever your workflow actually needs.

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

Whisper handles 90+ languages. `--lang` forces one, `--lang ""` auto-detects.

## Speed

Measured on an M4 Pro (48 GB), macOS 26.5, mlx-whisper 0.4.3, `large-v3-turbo`:

| Audio | Wall clock | Rate |
|---|---|---|
| 23 min, clean studio-style speech | 40 s | 34x |
| 43 min, real two-person interview | ~3 min | ~14x |
| 19 s clip, cold start with model load | 2 s | 7x |

Clean audio runs at the top of that range. Messy rooms, crosstalk and heavy accents pull it down. Either way it's minutes, not an afternoon, and the GPU does the work while you keep using the machine. A 25 MB upload cap and a queue position are no longer your problem.

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

Only the audio stream is ever decoded, so a 16 GB video costs the same as the MP3 inside it. There's no file size limit and no scratch WAV left behind.

## Gotchas

These cost real time to discover:

- **Whisper hallucinates loops on quiet tails.** On trailing silence it repeats the last phrase dozens of times past where the audio actually ended: *"...what are you interested, what are you interested, what are you interested..."*. `transcribe.py` strips a run of 4+ identical final segments and records the count in `loop_segments_stripped`. If a transcript ends in an obvious repeat, that's this, and the raw `.json` has the true end. `--no-clean` disables it.
- **The mlx_whisper CLI honors only one `--output-format`.** Passing it repeatedly silently keeps the last one. These scripts use the Python API and derive every format from the segments, so it doesn't bite here. It will if you script the CLI yourself.
- **Proper nouns are the weak spot.** Names, brands and jargon come back phonetically ("Kelemen" turns into "Kelliman"). That's what the confirm-list convention in CLAUDE.md is for. Don't let an agent silently "fix" them either.
- **`--lang en` is the default for a reason.** Auto-detect occasionally misreads a quiet opening and transcribes an English recording as Welsh.
- **The first run downloads 1.5 GB.** It looks like a hang. It isn't.

## Not on Apple Silicon

MLX is Metal-only. Everything else here (the loop stripping, paragraph grouping, frontmatter contract, CLAUDE.md agent layer) is portable. Swap the engine in `transcribe_file()` for one of:

- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), CTranslate2 under the hood, excellent on NVIDIA and respectable on CPU
- [`whisper.cpp`](https://github.com/ggerganov/whisper.cpp), runs anywhere, including a Raspberry Pi if you're patient

Both return the same segment shape (`start`, `end`, `text`), so nothing downstream changes.

## License

MIT. Take it, fork it, put your own frontmatter schema in it.
