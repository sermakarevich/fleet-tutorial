# How this codebase becomes a tutorial

One codebase grows tutorial by tutorial. A reader at tutorial 3 must be able
to run tutorial 3's code, not the finished runner. This document says how we
do that.

Method source: /Users/sergii/git/harness/docs/dev/TUTORIAL_METHOD.md and
coding rules in /Users/sergii/git/harness/AGENTS.md, adapted here for a swarm
runner instead of an agent harness.

## The three rules

1. **Write the final vision first.** `docs/dev/VISION.md` lists everything the
   finished runner does and shows its final folder tree. Every tutorial adds a
   file to that tree; no tutorial reshuffles it.
2. **One tutorial = one concept = one visible limitation fixed.** A tutorial
   starts with something the runner cannot do yet, adds the smallest code that
   fixes it, and ends with a command the reader can run and see.
3. **The git history is the tutorial.** Every tutorial ends in a git tag
   (`tut03`). The reader checks out the tag, runs `just tutorial`, reads
   `git diff tut02..tut03`. Code runs at the tag, never from `main`: `main`
   is the latest code and is not kept runnable for older tutorials. The
   documents stay on `main` for reading and for the book.

## What this means for the code

- Everything lives under `src/swarm/`. A concept first appears in its
  simplest form and a later tutorial replaces that form with the real one in
  the same file or folder. The diff between two neighbouring tags is still one
  concept. Nothing stays in the tree that the finished runner does not use: no
  teaching scripts, no old versions kept next to new ones.
- Every tutorial from 1 on runs through `python -m swarm`. The entry point
  grows with the series: one task, then a loop, then parallel workers.
- Every tutorial shows its concept with a real run. A tutorial that removes a
  limitation first shows the limitation with the code of the tutorial before,
  then the fix. The document copies both runs.
- Every tag has one `just tutorial` recipe that shows what that tutorial
  built. The recipe body changes from tag to tag; the name does not. No tag
  carries recipes for older tutorials, so `main` equals the last tag with
  nothing to strip.
- Every tutorial has tests that run without a network connection. Workers are
  faked at the subprocess boundary: a tiny fake harness script stands in for
  the real CLI.
- The layout follows AGENTS.md style rules: layers as folders, small files,
  imports point down.

## Who the reader is

An engineer who knows Python, git, and environment files, and has not built a
task runner. We explain queue ideas, worker behaviour, and design trade-offs
at medium-plus depth. We never explain programming basics; that reads as
Captain Obvious.

## What every tutorial document contains

Use `docs/dev/_TEMPLATE.md`. Every tutorial has two layers:

1. **In short**, about one screen, no code: the concepts in plain language,
   the scope (what we build now, why now, what we leave for later), the
   problem shown as a failing terminal exchange, and a file tree marking new
   and changed files.
2. **In detail**: how the new code works, the design decisions behind its
   shape and the alternatives rejected, at most one excerpt that carries the
   idea, how to run it, key takeaways, and what is still missing. The full
   change is `git diff` between the two tags; the document never walks it file
   by file.

A reader who reads only the first layer of every tutorial still gets the
whole story. The template ends with the writing rules: audience, prose, code,
and the rules that let the tutorials compile into one book.

## The tutorial plan

The tutorials tell one story. Each tutorial ends with a limitation, and the
next tutorial's concept is the answer to it. The order is in
`docs/dev/GOAL.md`, tut00–tut12. The story follows docs/ARTICLE.md, sections
1–17, compressed: TODO list and for-loop, checkpointing, human in the loop,
beads queue, parallel workers with leases, worktrees, retries, model routing,
the orchestrator, workflows, schedules, triggers and capstone.

The **Explained** points for each tutorial live in the GOAL table. They are
the checklist for whoever writes the tutorial document.

The plan may change; the three rules above do not.

## How a tutorial gets built

Two roles. The **manager** writes specs, reviews, and does small housekeeping:
renames, rules files, commits, tags, README rows, one-line document fixes.
**Fleet workers** (coder opencode, model
`opencode-go/muse-spark-1.3-contributor`) write every piece of code and every
tutorial document. The manager never writes code or tutorial prose itself; if
a spec is wrong, the manager fixes the spec and resubmits.

1. The manager writes two fleet task specs: one for the code with tests, one
   for the tutorial document. Both point at the coding rules, this file, and
   the template. The document spec carries the GOAL row and an acceptance
   checklist taken from the template rules.
2. Workers run in order on the tutorial work tree; the code task commits
   first. The code task also sets the `just tutorial` recipe body and adds the
   README table row.
3. The manager reviews against the template rules, runs `just tutorial` at the
   commit once, checks the document's "Run it" output against that run, and
   tags `tutNN`.
4. A tag may move while its tutorial is being polished. Once the next tutorial
   is tagged, the older tag is final and never moves again.

## Working agreements

Decisions taken while writing tutorial 0. They hold for every later tutorial.

- Documents live in `docs/tutorials/` on `main` and are identical at the tag.
  The README table lists one row per published tag.
- Nothing ships that nothing uses: no type markers, no placeholder modules, no
  recipes for older tutorials.
- Beads is the only queue. Workers never pick tasks from a text file after
  tut04. A task id is the only handle a worker needs.
- The writing rules live in one place, the template, and are applied to every
  tutorial document before it is accepted.
