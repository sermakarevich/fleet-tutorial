Pinned
Sergii Makarevych
@sermakarevich
From interactive AI to autonomous AI workers and workflows
A step-by-step guide to moving from interactive AI sessions to AI workflows and a fleet of autonomous AI workers.
Terminology used in this article
Interactive session — you type, the model answers, you type again.
Headless session — a session started by a script with a prompt, no human at the keyboard (for example claude -p "...").
Harness — the agent CLI that runs a session: Claude Code, OpenCode, Codex, pi.
Task — one unit of work you hand to the model, from a single command to a multi-file change. Later it is stored in the queue. Beads calls its records issues; colloquially each one is a bead.
Orchestrator — the program that decides which task runs where and when. Fleet is one.
Worker — one headless session executing one task.
The loop — the script that pulls tasks and spawns workers. It grows step by step through this article; from block 11 on I call it fleet.
Workflow — a saved sequence of tasks with dependencies.
Why interactive AI is not enough
Interactive AI is great for exploration: research, learning, designing a solution. You ask a question, you get an answer. In the basic case nothing is materialized; to recall the answer you have to go back to that session.
Or you ask for a task and wait for it to complete. If you have a list of tasks, you do them one by one, each time waiting for the previous one to finish.
The interesting question is: when you have a list of tasks, how do you execute them with AI as efficiently and as fast as possible?
In the default interactive scenario we ask the AI to do one task at a time, wait, then get distracted, then come back and ask for the next one. The gaps between tasks are wasted time.
Let’s improve one thing at a time, from an interactive session to a fleet of autonomous AI workers that you can orchestrate with little effort. In industry terms, we move from human-driven use, where you start and watch every step, to autonomous agents, where the system drives and you steer.
1. A TODO list
Instead of asking the model for a task interactively, instruct it to pull the next task from a to-do list. After each item the model removes it from the list, and you just ask it to pull the next one. Now you can pre-populate the list with everything you need and add new items while the model works. Iteration is just re-running the same prompt: “next item, please”.
2. Automate the iterations
To stop asking the model “next item, please”, replace yourself with a for loop in bash or Python. The loop calls the harness in non-interactive (headless) mode, for example claude -p, with a prompt saying “pull the next task from the to-do list and do it”. When the session exits, the loop starts a new one.
3. Checkpoint and resume
Headless sessions can fail in the middle of work: the context window fills up, you hit a usage limit, the network drops. We want the next session to resume where the previous one stopped.
The standard answer is checkpointing: save progress often, resume from the last checkpoint. There are several ways to do it. What I settled on is a dedicated folder per task where the session keeps small artifacts: the execution plan, what is already done, the final result. In my case these are STATE.md (a short progress note the worker rewrites as it goes), attempts/ (logs per attempt) and RESULT.json (the outcome). When a new session starts on a task that is a continuation of a failed one, the model first reads these artifacts, understands what is already done, and simply continues. This only works if the steps are idempotent, meaning a step that is run twice does no harm. Ask the model to plan its work that way.
4. Human in the loop
This is the human-in-the-loop (HITL) problem. By default a headless session cannot ask you a question; there is simply no tool for that. You have to create one. It can be anything: a CLI, an MCP (Model Context Protocol) server, a chat bot. I built an ask_human MCP tool with a Telegram integration, so all questions from headless (and interactive) sessions arrive in my Telegram, and the session blocks until I answer.
5. The bottleneck: one to-do list, many sessions
Now we want more than one headless session at a time. The to-do list becomes the blocker. Two sessions will inevitably pick the same item, because a plain text file has no safe way to claim an item (in queue vocabulary: no atomic claim, no lease). I tried several home-made approaches and all of them failed sooner or later.
6. Replace the to-do list with a task queue: beads
Beads (an open-source issue tracker built for AI agents) exists exactly for this: a task queue with safe claiming. It also gives you task dependencies, grouping tasks into epics, priorities, and a full history. Beads is a simple database on top of Dolt (a version-controlled SQL database) with a bd command-line tool.
What changes in the loop:
the to-do list is gone; tasks are added to beads;
the loop pulls the next ready task from beads;
the task status becomes in_progress when execution starts;
on success the task is closed;
on failure the task goes back to open and the next iteration picks it up again.
Later this last rule grew into a proper retry policy: the outcome of a failed attempt (crash, stall, context overflow, partial result) decides how many retries are allowed and how long to wait before the next one. After the retries are exhausted the task is moved to blocked and a question is sent to the human instead of retrying forever. Queue people call this a dead-letter queue; agent people call it escalation to the human in the loop. It is the same idea.
7. Scale the number of workers
With beads doing task management we can spawn several sessions without fear that a task runs twice. Beads decides which tasks may run in parallel through the dependencies between them. The loop decides how many workers to run, with an eye on our usage limits: ten workers can burn through a Claude subscription window in 20 to 30 minutes.
With many workers a new failure shows up: a worker crashes while holding a task, and the task stays in_progress forever. So the claim became a lease: a claim with a heartbeat that expires if the worker dies, and the task returns to the queue on its own.
8. Isolation: one worktree per worker
Several workers editing the same repository at the same time break each other’s work. The fix is one git worktree per task: the worker gets its own copy of the branch, does its work there, and the loop merges the result back into the base branch when the task is done. If the merge fails, the task does not fail silently: a repair worker is started to resolve the conflict, or the human is asked. This is the mechanism behind the “merge conflicts get resolved automatically” line at the end of the article.
9. Plan with a smart model, execute with a cheap one
To fit more tasks into a subscription usage window I started using smarter, more expensive models to plan and cheaper models to execute. This is model routing, or the planner/executor split. For example: Fable (Anthropic’s top model) creates the tasks, Sonnet (the cheaper one) executes them, and Fable reviews the result. This works better, but I still ran out of subscription limits too fast.
10. Support many harnesses
Technically it is simple to start a headless OpenCode, pi or Codex session instead of a headless Claude Code session. First I added OpenCode so text-processing tasks could run on Ollama with local models. Local models have become OK-ish recently, and Qwen 3.8 27B is just great.
The harness and model names became part of the task metadata in beads, and the loop respects them. Today the loop supports five harnesses: Claude Code, Codex, OpenCode, pi and agy.
Recently I discovered the OpenCode Go plan, which gives a ridiculous amount of tokens for the newest Muse Spark 1.3 contributor model for $10 a month. To understand how ridiculous: I decided to significantly rewrite the loop and expand its capabilities. Two workers ran non-stop for two days, executed 150 tasks, added 120,000 lines of code, removed 60,000 lines, and cost one dollar in total. That is about 25 cents per day for a great coder.
11. What do we have at this stage?
We talk to a smart model in an interactive session to understand the problem and design the solution. We ask it to submit tasks to beads with the right dependencies, harness and model for each task. The loop executes them.
This lets us build any graph of tasks. We can do spec-driven development this way. We can even build loops: a task that, when done, submits the next iteration as a new task.
At this point the loop is no longer a loop. It is a small orchestrator: a Python supervisor that watches beads, spawns workers in the right harness with the right model, isolates them in worktrees, merges their results, retries failures and asks the human when stuck. I call it fleet, and from here on I will use that name.
12. Extract graph patterns into workflows
When the same sequence of tasks repeats, for example spec-driven development (requirements, design, implementation, verification), wrap it into a workflow. A workflow is a higher-level abstraction on top of beads, task dependencies and workers: a saved definition of steps, where each step opens one ordinary task when its predecessors are done. Technically it is a DAG (directed acyclic graph) of steps, the same model Airflow or GitHub Actions use.
Example: a multi-step market research that monitors competitors’ promotions, monitors competitors’ pricing, collects the main market news, aggregates everything, distributes the report to the required channels, and stores it. You run the same sequence regularly, so it is much better to define it once than to submit the same tasks to beads every time.
13. Scheduling
Some tasks should run regularly, for example the market research above every working day, with the same inputs every time. So the loop gets a scheduler: a saved definition with a cron expression that opens an ordinary task or a workflow run when the time comes.
14. Event-driven triggers
Some tasks should start when an event happens, which is what event-driven means: process a document when an email with an attachment arrives, investigate a task when it gets blocked. So the loop gets triggers: a saved definition that watches a source of events and opens a task or a workflow run for every new event. In fleet a trigger polls its source on a timer and remembers which events it has already fired on, so each event starts exactly one worker.
15. A centralized, hierarchical LLM wiki
With many harnesses we must make sure they are all equipped the same way in terms of skills and tools. I stopped using each harness’s native skills mechanism, because I would have to maintain a version of every skill per harness. Instead all instructions live in a single knowledge base in the form of an LLM wiki: a tree of markdown files where every folder has an index that points to its entries, browseable with a small ai CLI. It has a skills section (plain markdown files with step-by-step instructions) and knowledge sections such as papers, research, tutorials and personal notes. Research tasks run by fleet write their artifacts into the knowledge base, it syncs to git every 5 minutes, and I read the output on a phone or a tablet.
The CLAUDE.md is tiny: it says that fleet exists, that the ai CLI is the way to reach the knowledge base, and little else. A simple procedure distributes the same file as AGENTS.md to the other harnesses from a single place.
16. Talking to fleet from anywhere
When I work on a complex task I use Fable, go deep into the topic, create the design and insert tasks into fleet.
When I am on the phone, Hermes (an open-source personal AI agent) helps: I talk to Hermes through its Telegram integration, and Hermes talks to fleet. I send it papers and articles to process and summarize, and the results land in the knowledge base.
17. What can we do at this stage?
Basically anything that can be automated with AI. We can spawn individual workers on request, on a schedule, or on an event. We can spawn a sequence of tasks of any shape as a workflow. We can spawn as many workers as we want; I peaked at around 30 workers for experimental purposes, which looks crazy. We can pick the harness and model per task based on its complexity and type, and on which provider offers the cheapest tokens today.
I have triggered workers resolving merge conflicts automatically. I have scheduled workflows that monitor AI papers, frameworks and articles and write summaries and tutorials into the knowledge base. And many smaller automations for my job and projects.
And $10 a month for OpenCode Go is all the execution power you need to get this today. A Claude subscription is nice to have for access to the very smart models, but apart from Fable they are not really needed: Muse Spark in OpenCode Go is good enough for most execution tasks once the design is well defined.