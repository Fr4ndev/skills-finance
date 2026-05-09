# Implementation Patterns for Automation and Scheduling

Read this after a route is selected in `SKILL.md`, or when you need concrete implementation guidance. Each pattern corresponds to a route in the main skill.

## Pattern 1: Schedule → Manus Execution

Use when the task needs Manus-level judgment, writing, research, or connector access, and the trigger is a simple fixed time.

| Concern | Guidance |
| --- | --- |
| Trigger | Use the schedule capability for fixed-time or interval triggers. |
| Execution | Manus performs the task directly. Best for work that requires judgment, synthesis, or connector access. |
| Context | Reuse the same session when historical continuity is valuable; use isolated runs when context cost or independence matters more. |
| Prompt | Describe what to do at execution time — data sources, output format, success criteria, failure behavior. Avoid "do the same thing as before" unless session context is intentionally reused. |
| State | For incremental tasks, track processed items, last-run timestamp, or cursors in a durable place. |
| Cost | Each run consumes Manus credits. Suitable for low-frequency, high-value tasks. Not suitable for high-frequency or scaling workloads. |

## Pattern 2: WebDev + Cron

Use when the execution is deterministic (API call, comparison, notification), the user may want a management GUI, the scope may grow, or cost/latency matters. WebDev provides a managed backend with cron job support — no infrastructure to manage.

| Concern | Guidance |
| --- | --- |
| Trigger | WebDev cron jobs run on a schedule. Configure interval in the WebDev backend. |
| Execution | Deterministic code in the WebDev backend — API calls, data processing, rule-based checks, notifications. No Manus involved at runtime. |
| GUI | WebDev naturally supports a frontend for managing parameters (watchlists, thresholds, recipients). Add one when the user will adjust settings over time. |
| External APIs | For public data (stock prices, weather, exchange rates), call external APIs directly from the backend. The user may need to obtain API keys. |
| Notifications | For Slack, Telegram, email, etc., the user sets up the integration (webhook URL, bot token). Guide them through it. |
| Constraints | Stateless execution, 15-minute timeout per job, 1 vCPU / 512 MB per pod. Sufficient for API polling, data checks, and notifications. Not suited for heavy compute. |
| Cost | Free per run after initial setup. The user only pays for external API usage if applicable. |

Read `persistent-computing` for full WebDev capabilities and limitations.

## Pattern 3: WebDev + External Trigger

Use when the user wants a web app or dashboard that also updates itself, and the update is driven by an external trigger (schedule, event, or Manus API) rather than a simple WebDev cron.

| Component | Responsibility |
| --- | --- |
| WebDev UI | Display results, collect user input, expose settings and dashboards. |
| Storage | User settings, generated content, run history, published state. |
| Trigger | Use schedule for simple time-based updates. Use Persistent Sandbox or external platform for event-driven or logic-heavy triggers. |
| Execution | Use Manus API for high-quality work; use deterministic code or built-in LLM for stable, low-subjectivity substeps. |
| Publishing | Prefer preview/approval for public or high-impact updates; allow automatic publishing only after explicit user consent. |

## Pattern 4: Persistent Trigger + Manus API

Use when the workflow needs a durable or complex trigger (webhooks, polling with state, filtering, deduplication, throttling) but the actual work should be done by Manus.

| Layer | Responsibility |
| --- | --- |
| Trigger Host | Receive webhooks, poll external APIs, maintain state, deduplicate, throttle, retry. Runs in Persistent Sandbox, third-party cloud, or external platform. |
| Manus Execution | Perform high-quality analysis, writing, research, cross-tool reasoning, connector-aware work. Invoked via Manus API. |
| Result Handling | Poll or receive webhook completion, download attachments, write results back, notify users. |
| Observability | Track processed IDs, run logs, failures, retry counts, last successful execution. |

Typical examples: Slack/Discord bots that need judgment, GitHub webhook → summarize + notify, RSS monitoring with semantic filtering, alert triage with escalation.

Read `manus-api` for API details. Read `persistent-computing` for hosting options.

## Pattern 5: Persistent Service

Use when the service must stay online independently — always-on bots, webhook endpoints, fixed IP, Docker, queues, or self-hosted platforms.

| Need | Why persistent computing is required |
| --- | --- |
| Always-on process | Must remain online outside any Manus session. |
| Webhook endpoint | External systems need a stable receiver. |
| Fixed IP | DNS records, firewall allowlists. |
| Docker / custom runtime | Packages or services beyond WebDev's managed path. |
| Queues / background workers | Jobs must keep running independently. |

Read `persistent-computing` before recommending or deploying. Explain why WebDev or schedule is insufficient, and mention free or simpler alternatives before recommending a paid persistent environment.

## Pattern 6: Default Sandbox

Use for one-off or current-session automation: data cleanup, batch transformation, exploratory scraping, local file processing, short-lived API calls, or temporary glue scripts.

Do not rely on the default sandbox for unattended long-running services, webhook receivers, or background workers that must survive hibernation. If a sandbox script becomes a recurring need, reassess whether it should move to schedule, WebDev + cron, or persistent hosting.

## Safety and Operations Checklist

Apply this to any recurring or event-driven workflow, regardless of pattern.

| Area | Check |
| --- | --- |
| State | Store last-run timestamp, processed IDs, cursors, and output history for incremental tasks. |
| Idempotency | Make repeated triggers safe — avoid duplicate sends, posts, or destructive actions. |
| Retries | Decide which failures retry, how many times, and when to alert the user. |
| Logs | Record trigger time, input identifiers, execution status, output location, errors. |
| Secrets | Use environment variables or a secret store. Never hard-code API keys. |
| Permissions | Use least-privilege API keys and connectors. |
| Human approval | Require confirmation for posting, emailing, purchasing, deleting, or modifying important external data unless the user explicitly approves full automation. |
| Cost | Explain cost shape: Manus credits per run, WebDev hosting, persistent compute monthly cost, external API costs. |
