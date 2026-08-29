# CELPIP content and format research log

This log records public facts used to design the independent practice platform.
It does not authorize copying official questions, recordings, transcripts,
images, or paid materials. All practice prompts and media in this repository
must remain original and traceable through the editorial workflow.

## Listening revalidation — 29 August 2026

Primary sources:

- [Official CELPIP test format](https://www.celpip.ca/take-celpip/test-format/)
- [Official 2026 Listening Pro Study Pack](https://www.celpip.ca/wp-content/uploads/2026/03/Listening-Pro-Study-Pack-2026.pdf)
- [Official free resources and Listening tips](https://www.celpip.ca/prepare-for-celpip/free-resources/)
- [Official results and scoring explanation](https://www.celpip.ca/take-celpip/test-results/)
- [Official CELPIP FAQ](https://www.celpip.ca/take-celpip/faqs/)

Verified product rules:

- The CELPIP-General Listening component is currently listed as 46–55 minutes
  and six parts: Problem Solving (8 questions), Daily Life Conversation (5),
  Information (6), News Item (5), Discussion (8), and Viewpoints (6).
- Listening answers are computer-scored as correct/incorrect; blanks are
  incorrect. The official site publishes approximate whole-component ranges,
  but a short practice set must report raw practice accuracy rather than apply
  that table as though it were a complete official component.
- Official preparation guidance says each recording is heard once, recommends
  note-taking, and explains that navigation/timing differs between groups of
  parts. Parts 4–6 show sentence-completion questions and four choices together;
  Parts 1–3 use a different sequential question flow.
- The real test can contain indistinguishable unscored Listening or Reading
  items. These belong in the later full-mock assembler, not in short Learn sets.
- CELPIP-General is the four-skill immigration product. General LS is not the
  target of this application.

Implementation interpretation:

- Learn mode may replay original practice audio and releases the transcript
  after an answer so the learner can study paraphrase and evidence.
- Timed Practice grants one playback and withholds transcript, corrections,
  and evidence until submission. This deliberately trains the official
  one-listen expectation without claiming that a short set reproduces the full
  official timing or scoring scale.
- Seed audio may use a clearly identified synthetic voice during development.
  Synthetic output is reviewed for transcript fidelity and is never described
  as an official recording or exact test-centre audio.

## Writing revalidation — 29 August 2026

Primary sources:

- [Official CELPIP test format](https://www.celpip.ca/take-celpip/test-format/)
- [Official 2026 Writing Pro Study Pack](https://www.celpip.ca/wp-content/uploads/2026/03/Writing-Pro-Study-Pack-2026.pdf)
- [Official free resources and Writing tips](https://www.celpip.ca/prepare-for-celpip/free-resources/)
- [Official results and scoring explanation](https://www.celpip.ca/take-celpip/test-results/)

Verified product rules:

- CELPIP-General Writing has two tasks in this order: Writing an Email and
  Responding to Survey Questions. The component is currently listed at about
  53 minutes total.
- Public preparation guidance suggests roughly 27 minutes for the email task
  and 26 minutes for the survey task, and a response of about 150–200 words for
  each. These are learner-facing suggestions, not official per-task hard limits.
- Writing is assessed independently by four to six qualified, trained raters
  across Content/Coherence, Vocabulary, Readability, and Task Fulfilment on the
  0–12 scale. A short practice tool cannot reproduce that rating, so this
  platform presents those four dimensions only as an honest self-review
  checklist and never outputs an estimated CELPIP level for a practice response.

Implementation interpretation:

- Seed prompts are original Canadian-context scenarios authored for this
  repository. Each carries structured prompt data (task kind, scenario,
  requested points, survey options, target word range, suggested duration, and
  learning guidance) that is frozen into the session snapshot at start time.
- Writing content stores no objective questions or answer keys. Content
  validation is skill-aware: for `writing` task types, zero questions is valid
  and expected, and the structured prompt schema is validated instead.
- A submitted writing response is immutable. Autosave is revision-aware and
  idempotent, and the server — not the client — computes the stored word count.
- Practice writing feedback is explicitly non-official: rubric dimensions are
  shown for self-review, and no field claims an automatic CELPIP score or level.
