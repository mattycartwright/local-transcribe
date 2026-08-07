```
   ▁▂▄█▆▃▁▂▅█▇▄▂▁▃▆█▄▂▁▁▂▅▇█▅▃▁▂▄▆█▃▁▂▁▄▇█▅▂▁▃▅█▆▂▁
   └────────────────────┬──────────────────────────┘
                        │   your mac. 40 seconds. $0.
                        ▼
                  transcript.md
```

# local-transcribe

Transcribes stuff on your computer. For free. Forever. That's it, that's the repo.

```bash
brew install ffmpeg && pip3 install mlx-whisper
python3 scripts/transcribe.py that-thing-you-recorded.mov --title "That Thing"
```

### what an hour of audio costs

| | |
|---|---|
| Rev | $15.00 |
| Sonix | $10.00 |
| Otter Pro | $8.33/mo, and it cuts you off at 20 hrs |
| OpenAI's API | $0.36 |
| this | nothing. run it a thousand times. |

### how long you wait

| 2.5 min voice memo | 6 seconds |
| --- | --- |
| 23 min podcast | 40 seconds |
| 43 min interview | 3 minutes |
| that folder of 300 files | go to bed, it'll be done |

### what you type

| one file | `transcribe.py x.mov --title "X"` |
| --- | --- |
| a whole folder | `bulk_transcribe.py ~/footage --out ~/notes` |
| who said what | open the repo in Claude Code, say "label the speakers" |

You get a `.md` with frontmatter and actual paragraphs, an `.srt`, timestamps, and the raw JSON. Drop it in Obsidian and walk away.

### the CLAUDE.md thing

Whisper hands you a wall of text and has no clue who's talking. Turns out you don't need a fancier model for that, you just need to read it and figure out who's asking questions and who's answering them. Which is a thing an LLM is good at.

So [CLAUDE.md](CLAUDE.md) is that job, written down: fill in the frontmatter, name the speakers, flag every proper noun it probably got wrong. A prompt living in the repo next to the code. Steal it, change the fields, it's yours.

```
                    ┌─────────────────┐
   your voice ─────▶│  no internet    │─────▶ words
                    │  no account     │
                    │  no meter       │
                    └─────────────────┘
```

Apple Silicon only (that's the free GPU part). MIT.
