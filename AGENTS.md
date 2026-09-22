# Coding rules for this repository

These rules apply to every file in this repo: code, tests, scripts, and docs.
They bind humans, Claude Code, and fleet workers alike.

## Values, in priority order

1. **Simplicity** — the smallest thing that works. No layers "for later".
2. **Readability** — code reads top to bottom like a short story.
3. **Evolvability** — one module per runner job, so the next step adds a file
   instead of rewriting one.
4. **Maintainability** — every behaviour has a test that runs without network.

## No comments unless absolutely necessary

- Do not write `#` comments. If code needs a comment to be understood, rename
  or split it instead.
- The only exception is a fact the code cannot show, such as a vendor quirk or
  a workaround for a bug. Then one short comment, with the reason.
- One short docstring per module and per public function is allowed. It says
  what the thing is for, in one to three plain sentences.
- A docstring never restates a value, a name, or a detail of how the code
  works. Those change with a one-line edit elsewhere and the prose silently
  rots. `"""Slash commands the terminal chat accepts."""` is wrong the moment
  the prefix stops being a slash.
- If the name already says the purpose, there is no docstring.
  `class Command(StrEnum)` in `queue/beads.py` needs none.

## Plain English

- Use simple, everyday words in names, docstrings, docs, and commit messages.
- Spell out every abbreviation the first time it appears in a document (for
  example: LLM, large language model).
- Short sentences. One idea per sentence.

## Hierarchy: high calls low, folders show the layers

- Code is organised top-down. A higher-level function calls lower-level
  functions, never the other way round. Imports point down the hierarchy only;
  no cycles.
- Folders mirror the layers. The entry point sits at the top, then the runner
  loop, then task handling, then the worker transport, then settings at the
  bottom.
- Each file is small and does one thing. A file that needs a second job gets a
  sibling file, not a second class.
- A file name says what the file does in one or two plain words (`loop.py`,
  `queue.py`), never `utils.py`, `helpers.py`, `common.py`.
- Each folder has a short `__init__.py` docstring saying what layer it is and
  what lives below it.

## Prompts live in text files

- Every prompt sent to the model is a `.txt` file next to the code that uses
  it, for example `src/swarm/worker/prompts/system.txt`.
- Python loads the file and fills named placeholders such as `{task}`. No
  prompt text inside Python strings.
- One prompt per file. The file name says what the prompt is for.

## No hardcoded values

- A literal that carries meaning gets a name. Compare against the name, never
  the raw value.
- Group related names in one place: a `StrEnum` for a fixed set of choices
  (task states, worker kinds), a small frozen dataclass or module-level
  constants for the rest (header names, id prefixes, file names).
- Anything a user might want to change (model name, base URL (uniform resource
  locator), user agent, timeouts) is a field in `Settings` with an environment
  override, not a literal in the code that uses it.
- One fact, one place. A value that follows from another is derived in code,
  never typed again.
- Framework-required keys such as a queue library's state key are the one
  exception; they are part of the library's contract, not our choice.

## Project conventions

- Python 3.12+, managed by `uv`; run everything through `uv run` or `just`.
- Settings, when needed, are read with environment variables under the single
  prefix `SWARM_`. Code reads them through one `Settings` object, never from
  the environment directly.
- `.env.example` lists every variable, uncommented, with its default. Nothing
  in it is a comment except the one line that says where the key comes from.
- Secrets live in `.env` and are never printed, logged, or committed.
- Nothing ships that nothing uses: no marker files, no placeholder modules, no
  recipes kept for older tutorials.
