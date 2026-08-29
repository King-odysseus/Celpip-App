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
