# Audited AI services

The application uses a provider-neutral database queue. `AI_PROVIDER=fake` is
deterministic for development and tests; `AI_PROVIDER=openai` activates the live
adapter when `OPENAI_API_KEY` is present. The API key is backend-only and must
never be added to `VITE_*`, source control, or browser storage.

## Responsibilities and boundaries

- Writing: a submitted response is sent as untrusted data to a versioned,
  structured rubric prompt.
- Speaking: the private recording is transcribed, then the transcript and frozen
  task are evaluated with the same audited schema.
- Question sets: `queue_ai_content_draft` creates an original Reading or
  Listening job. Successful output can only become an `AI-generated draft` in
  Django Admin; the existing separate-reviewer rule prevents automatic or
  self-publication.
- Media: the provider interface implements GPT Image prompt scenes and TTS for
  original listening scripts. These binaries must enter the private/editorial
  asset workflow and be reviewed before a content version can be published.
- Evals: evaluator quality is tested separately from learner-facing estimates.
  The application never presents OpenAI output as an official CELPIP result.

Every job records its provider, model, prompt/schema versions, input snapshot,
attempt count, external response identifier, token usage, safe failure, and
immutable final output. Live Responses requests set `store=false`.

## Operations

```powershell
# Queue an original objective draft (never publishes it)
python manage.py queue_ai_content_draft reading_correspondence "Tenant recycling changes" --difficulty 2

# Run one job for a deployment smoke test
python manage.py run_ai_worker --once

# Run the worker continuously in a separate supervised process
python manage.py run_ai_worker
```

## Listening audio synthesis

Stored Listening audio is generated once and reused. `regenerate_listening_audio`
turns each reviewed transcript into a validated WAV through an ordered list of
speech providers, `LISTENING_TTS_PROVIDER_ORDER` (default `openai,azure,local`):

1. **OpenAI natural TTS** — reuses the server-side `OPENAI_API_KEY` and
   `OPENAI_TTS_MODEL`, requesting WAV output and alternating
   `LISTENING_OPENAI_VOICES` (female voice first, male second) across speakers.
   When `MediaAsset.speaker_genders` maps a speaker label to `female`/`male`,
   that speaker is assigned the matching voice instead of by order of first
   appearance, so a male-first dialogue is not gender-reversed.
2. **Azure Speech neural TTS** — server-side `AZURE_SPEECH_KEY` +
   `AZURE_SPEECH_REGION`, official REST endpoint, RIFF PCM WAV, Canadian voices
   `LISTENING_AZURE_VOICES` (`en-CA-ClaraNeural`, `en-CA-LiamNeural`).
3. **local** — terminal fallback that *retains* the existing validated recording
   (first produced by `scripts/generate-listening-audio.ps1` on Windows).

This order is deliberately **independent of `AI_PROVIDER`**, so evaluation can run
on the fake provider while audio uses a live vendor. Missing credentials, provider
errors, and invalid/corrupt/too-short output all fall through to the next provider.
Every candidate is strictly validated as PCM WAV before use; the file is replaced
atomically (temp file + `os.replace`) only after validation, and the `MediaAsset`
row — duration, byte size, checksum, and safe provider/model/voice provenance — is
updated only after the file is in place. A working recording is **never** destroyed
when every provider fails. Secrets never enter logs, responses, metadata, or
provenance. Costs: OpenAI and Azure TTS are paid/metered (Azure has a limited free
tier); with no credentials the pipeline stays on `local` at no cost. Generated
audio is synthetic and unofficial; old stored WAVs remain until regenerated.

```powershell
# Preview only; calls no provider and writes nothing
python manage.py regenerate_listening_audio --dry-run
# Regenerate one set, or omit --slug for all; --force resynthesizes valid audio
python manage.py regenerate_listening_audio --slug apartment-heating-plan --force
python manage.py regenerate_listening_audio --force
```

## Separate per-provider renditions

`generate_listening_renditions` produces an alternative `AudioRendition` for a
specific remote provider (`openai` and/or `azure`) without touching the
canonical `MediaAsset` WAV. It never falls back to another vendor and never uses
the `local` provider. Each rendition is written to its own deterministic private
path — `listening_renditions/{provider}/{canonical-id}.wav` — atomically (temp
file + `os.replace`) only after strict WAV validation, then recorded as a
checksummed row. A database failure rolls the file back; synthesis is idempotent
(an identical checksum on an existing READY rendition is left untouched);
missing credentials mutate nothing; and per-asset failures are isolated from the
rest of the batch. Secrets never enter logs, metadata, or provenance.

```powershell
# Preview only; reports availability without calling any provider
python manage.py generate_listening_renditions --provider openai --dry-run
# Both providers (repeatable or comma-separated), all sets
python manage.py generate_listening_renditions --provider openai --provider azure --force
python manage.py generate_listening_renditions --provider openai,azure --force
# One set, one provider, without forcing already-valid renditions
python manage.py generate_listening_renditions --provider openai --slug apartment-heating-plan
```

Writing and Speaking submissions enqueue feedback automatically. The frontend
polls the owner/guest-authorized feedback endpoint and clearly labels the result
as an AI-assisted practice range. The Speaking Attempt 1 vs Attempt 2 comparison
endpoint is derived entirely from the two stored AI-feedback artifacts; it never
issues a new job or provider call.

## First-party implementation references

- [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Current model catalog](https://developers.openai.com/api/docs/models)
- [GPT Image 2](https://developers.openai.com/api/docs/models/gpt-image-2)
- [Audio and speech](https://developers.openai.com/api/docs/guides/audio)
- [Evals API](https://developers.openai.com/api/reference/resources/evals/methods/create)
