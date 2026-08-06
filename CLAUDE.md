# CLAUDE.md

Instructions for an agent working in this repo. Whisper produces raw text. Your job is the layer above it: run the transcription, fill the frontmatter, and turn an undifferentiated stream of words into a labeled, readable transcript without inventing anything.

This file is written for Claude Code but any agent that reads a project instruction file can follow it, and a human can read it as a checklist.

---

## 1. Run the transcription

Never write your own ffmpeg or Whisper invocation. Use the scripts.

```bash
# one file
python3 scripts/transcribe.py "SOURCE" --title "Short Title"

# a folder, or several paths
python3 scripts/bulk_transcribe.py PATH [PATH ...] --out DIR --skip-existing
```

If the user already knows who is in the recording, pass it through so it lands in the frontmatter:

```bash
python3 scripts/transcribe.py interview.mov --title "Founder Interview" --speakers "Ari,Jordan"
```

Rules:

- **A URL is not a source.** Download it first (`yt-dlp URL -o file.mp4`), then transcribe the local file.
- **Don't set `--model` unless asked.** `large-v3-turbo` is the right default. Reach for `whisper-large-v3-mlx` only when turbo visibly mangled a hard recording.
- **Don't pass `--no-clean`** unless the user needs Whisper's raw tail. The loop it strips is a hallucination, not content.
- **Long files are fine.** Don't chunk, don't downsample, don't apologize for the wait. A 43-minute interview takes about 3 minutes.

Then report: output folder, real-time speed, word count, and whether a loop was stripped. If `loop_segments_stripped` is above 0, say so plainly, because it means the audio had a quiet tail.

---

## 2. Fill the frontmatter

`transcribe.py` writes YAML frontmatter into the `.md` and fills only what it can know for certain. The rest is yours.

| Field | Owner | Notes |
|---|---|---|
| `title` | script | From `--title`. Improve it only if the user asks. |
| `source`, `source_path` | script | Never edit. Provenance. |
| `recorded` | script | File mtime. Correct it if the user gives you the real date. |
| `transcribed` | script | Never edit. |
| `duration`, `duration_seconds` | script | Never edit. |
| `language` | script | Never edit. |
| `model` | script | Never edit. |
| `words` | script | Never edit. Re-count only if you rewrote the body. |
| `loop_segments_stripped` | script | Never edit. A quality signal worth reading. |
| `speakers` | **you** | Full names once you know them. Empty list if a monologue. |
| `summary` | **you** | 1 to 2 sentences. What was actually covered, not what it was "about". |
| `topics` | **you** | 3 to 6 lowercase tags. Specific over generic. |
| `labeled` | **you** | `true` only after you produce a `.labeled.md`. |

**How to fill each:**

- **`speakers`** goes from a hint to the truth. `--speakers "Ari,Jordan"` puts first names in. Upgrade to full names when the recording states them, and leave first names alone when it doesn't. Do not guess a surname.
- **`summary`** should survive being read six months later with no memory of the recording. "Jordan walks through why the company started as a marketplace and what broke when they tried to sell direct" beats "a conversation about business strategy". No adjectives about how good the conversation was.
- **`topics`** are retrieval keys, not a description. `["marketplaces", "founder story", "pricing"]`, not `["business", "interesting", "long"]`.
- **`labeled`** is a claim you have to earn. Flip it to `true` in the labeled file only.

**Editing rule:** rewrite the frontmatter block in place and leave the body untouched on this pass. Enriching metadata and editing prose are two different jobs, and mixing them is how transcripts quietly drift away from what was said.

### Adding your own fields

The schema is not sacred. If the user's workflow needs more, add it and keep it consistent across the project. Useful ones:

```yaml
client: "northwind"          # who this belongs to
project: "q3-brand-refresh"  # what it feeds
type: "interview"            # interview | podcast | voice-memo | talk | meeting
status: "raw"                # raw | labeled | approved
usable_clips: 4              # counted, not guessed
confirm: ["Kelemen", "Sequoia"]   # proper nouns needing a human check
```

Anything you cannot verify from the audio does not go in the frontmatter. `sentiment: "positive"` is a guess wearing a metadata costume.

---

## 3. Add speaker names

**Whisper does not diarize.** It has no idea how many people are talking. There is no flag for this, and any tool that claims otherwise is running a separate model. What you have instead is the content, and for a two or three person recording that is usually enough.

### Read the right file

Work from `Title.timestamped.txt`, not the `.md`. Turn boundaries live in the timestamps. A 1.5 second gap followed by a question is almost always a handoff.

### Assign speakers from these signals, in order of reliability

1. **Direct address.** "So Jordan, walk me through it" means the next voice is Jordan.
2. **Self-identification.** "When I started the company" belongs to the founder, not the interviewer.
3. **Question versus answer shape.** Interviewers ask short questions and give short backchannel ("right", "totally", "say more"). Guests deliver long paragraphs.
4. **Topic ownership.** One person holds the detail: numbers, dates, internal names. That's the subject.
5. **Register.** Interviewers restate and summarize ("so what you're saying is"). Guests narrate.

### Write it out

Create a new file next to the others, never overwrite the original:

```
Founder-Interview.labeled.md
```

Exact format:

````markdown
---
title: "Founder Interview"
speakers: ["Ari Nakamura", "Jordan Reyes"]
summary: "Jordan walks through why the company started as a marketplace
  and what broke when they tried to sell direct."
topics: ["marketplaces", "founder story", "pricing"]
labeled: true
confirm: ["Kelemen", "Northwind Supply"]
---

# Founder Interview

*Speakers were assigned by content, not by voice, so eyeball anything that
reads oddly. The text is lightly cleaned: filler removed, punctuation added,
wording faithful. A 6-segment hallucination loop was stripped from the tail.*

*Confirm these: "Kelemen" (corrected from "Kelliman"), "Northwind Supply"
(corrected from "north wind supply"). Heard but unverified: the professor's
name at 14:02, the 2019 revenue figure at 22:40.*

---

**ARI:** Take me back to the beginning. What was the first version?

**JORDAN:** The first version was a spreadsheet, honestly. We had maybe
forty suppliers in it and I was emailing every single one by hand.

That went on for about nine months before anything broke.

*[Phone rings, brief pause while Jordan takes it.]*

**ARI:** And what broke first?

**JORDAN:** Pricing. Always pricing.

*[Transcript ends here.]*
````

Format rules:

- `**NAME:**` in caps, one label per turn. A multi-paragraph turn gets one label, then plain paragraphs.
- The **methodology note in italics** is required. It tells the reader speakers came from content, that the text was lightly cleaned, and whether a loop was stripped.
- The **confirm list** is required whenever you corrected a proper noun or heard one you can't verify. Split it: what you corrected, and what you're unsure of. This is the single most useful thing you produce, because Whisper mangles names and a wrong name in a published quote is a real problem.
- Non-interview moments (filming direction, interruptions, the dog) become brief *[italic stage notes]*, not verbatim text.
- End with `*[Transcript ends here.]*` so a truncated file is obvious.

### Cleanup: what you may and may not change

**Allowed:**
- Remove filler ("um", "uh", meaningless "you know" and "like")
- Add punctuation, capitalization, paragraph breaks
- Merge stutters and false starts ("I, I think we, we should" becomes "I think we should")
- Fix Whisper's obvious mistranscriptions of proper nouns, and list them in the confirm block

**Not allowed:**
- Paraphrasing, tightening, or "making it flow"
- Reordering anything
- Adding a transition or connective that wasn't spoken
- Correcting a fact the speaker got wrong. Keep their words. Flag it in the methodology note instead.
- Smoothing grammar into something they didn't say

Every word in the labeled file must trace to something in the `.json`. If you can't point at the segment, it doesn't go in.

### When you genuinely can't tell

Use `**SPEAKER 1:**` and `**SPEAKER 2:**` and say so in the note. Guessing a name is worse than admitting you don't have one. If two people have the same speech pattern and no one is ever named, that's the honest output.

Three or more speakers with heavy crosstalk is where content-based assignment falls apart. Say that plainly rather than shipping a confident wrong answer. If the user needs true diarization, point them at `pyannote-audio`, which is a separate model and a separate install.

---

## 4. Optional derived outputs

Only when asked. Each is a new file, and the original `.md` and `.json` stay untouched.

- `Title.chapters.md`: a `[mm:ss] Chapter title` list built from the timestamped file
- `Title.quotes.md`: pull quotes with timestamps, verbatim, for social or an article
- `Title.actions.md`: commitments and owners from a meeting recording
- `Title.clips.md`: clip candidates with in and out timestamps, for a video editor

Every one of these cites timestamps. A quote without a timestamp is unverifiable, which defeats the point.

---

## 5. Rules that don't bend

1. **Never invent.** Not a name, not a number, not a company, not a transition. A gap gets flagged, never filled.
2. **Never overwrite the source of truth.** `.json` and the original `.md` are immutable. Enrichment creates new files.
3. **Never claim `labeled: true`** without a labeled file behind it.
4. **Never silently fix a fact.** Flag it in the note and keep their words.
5. **Never present a corrected proper noun as certain.** It goes in the confirm list.
6. **Don't reach for the API.** This repo exists because the whole pipeline is local and free. If MLX fails, fix MLX.

---

## 6. Gotchas worth knowing before you debug

- **A repeated phrase at the end of a transcript is a hallucination, not content.** Whisper loops on trailing silence. The script strips runs of 4+ and records the count. Check `loop_segments_stripped` before you assume the recording ended strangely.
- **The mlx_whisper CLI honors only one `--output-format`.** Passing it repeatedly silently keeps the last. These scripts use the Python API and derive all formats from segments, so it can't bite here, but it will if you write your own CLI call.
- **First run downloads 1.5 GB** and looks like a hang. Wait it out.
- **Batches load the model once.** `bulk_transcribe.py` keeps it resident, so 50 clips is not 50 model loads. Don't loop `transcribe.py` in a shell script to do the same job.
- **`--lang en` is the default and it matters.** Auto-detect occasionally picks the wrong language on a quiet opening and transcribes an English recording into Welsh. Pass `--lang ""` only when the source really is unknown.
- **Timestamps drift slightly on long files.** Fine for chapters and clip selection. Verify before frame-accurate editing.
