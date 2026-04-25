# Agent 13 — Async Agent

## What it demonstrates
**Non-blocking background execution** — instead of waiting for the LLM to finish (which can take 15–30 seconds),
this agent returns a `job_id` immediately (< 1 second), runs the LLM call in a background thread using `ainvoke()`,
stores the result in Redis, and lets the user poll for the result when ready.

## New concepts vs Agent 12 (Structured Output Agent)
| | Structured Output Agent (Lab 12) | Async Agent (Lab 13) |
|---|---|---|
| Pattern | Single blocking call | Non-blocking + polling |
| Return | Immediate result | `job_id` immediately, result later |
| LLM call | `llm.with_structured_output()` | `await llm.ainvoke()` in background thread |
| Storage | None — result in memory | Redis with TTL |
| Use case | Data extraction | Long-running tasks, webhook callbacks |

## LangGraph concepts
- `TypedDict State` with `user_input`, `job_id`, `status`, `result`
- 3-node graph with conditional routing from `START`:
  - text → `node_start` (submit job)
  - `job:<id>` → `node_poll` (check Redis)
  - `webhook:...` → `node_webhook_demo` (blocking demo)
- `add_conditional_edges(START, route)` — routing happens before any node runs

## Async concepts
- **`ainvoke()`** — async version of `llm.invoke()` — must be called with `await` inside `async def`
- **`async def _run_llm_async()`** — coroutine that calls `ainvoke()` without blocking
- **`asyncio.run()`** — creates a new event loop in the background thread to run the coroutine
- **`threading.Thread`** — runs the async coroutine in a separate thread, keeping the main thread free
- **`asyncio.sleep(15)`** — async sleep — yields control instead of blocking (vs `time.sleep()`)

## Redis concepts
- **`redis.Redis()`** — connection to Redis — one instance shared across all requests
- **`setex(key, ttl, value)`** — write with automatic expiry (TTL = Time To Live)
- **`get(key)`** — read value; returns `None` if key expired or never existed
- **`JOB_TTL = 3600`** — jobs expire after 1 hour automatically

## Webhook concept
- In production, instead of polling, the agent calls `httpx.AsyncClient().post(callback_url, json=result)`
- The webhook receiver gets the result automatically — no polling needed
- `node_webhook_demo` simulates this with a 5-second intentional block — demonstrates WHY blocking is bad

---

## STEP 0 — Install Docker (required before anything else)

> This lab requires **Redis running in Docker**. You must complete this step before creating any files.
> Redis stores job results so they survive between requests and expire automatically after 1 hour.

---

### 0.1 — Download Docker Desktop

Go to this page in your browser and download the installer for Windows:

**https://www.docker.com/products/docker-desktop/**

Click **"Download for Windows"** — the file is called `Docker Desktop Installer.exe` (~600 MB).

---

### 0.2 — Install Docker Desktop

> ⚠️ **You need admin rights** — right-click the installer → **"Run as administrator"**.
> If you do not have admin rights, ask your IT department or manager.

1. Double-click `Docker Desktop Installer.exe`
2. Right-click → **Run as administrator** (important — without this it may fail silently)
3. Follow the installer — accept all defaults
4. At the end it will ask to **restart your computer — click Yes and let it restart**
5. **Do NOT close the installer tab or cancel the restart** — the restart is required to activate the virtualization driver

After restart, Docker Desktop opens automatically. Wait until the bottom bar shows **"Engine running"**.

---

### 0.3 — Disable Kernel DMA Protection in BIOS (corporate laptops only)

> ⚠️ This step is required on **Atos/Eviden corporate laptops** and other managed machines.
> Docker needs hardware virtualization enabled. Corporate security policies sometimes block it via BIOS.
> Without this, Docker will show **"Virtualization support not detected"** and won't start.

**Step-by-step:**

1. **Restart your computer** — do NOT just shut down, you need a full restart to enter BIOS
2. **Press the BIOS key** immediately when the screen turns on — before Windows loads
   - Atos laptops: usually **F2** or **Del** — watch the screen for the key hint
   - If you miss it, restart again and try faster next time
3. In the BIOS menu, navigate to:
   ```
   Security → Virtualization
   ```
4. Find the option called **"Kernel DMA Protection"** (may also appear as "DMA Protection")
5. **Uncheck it / set it to Disabled**
6. Save and exit — usually **F10** → confirm Save
7. Windows boots normally — Docker Desktop should now start without errors

> **Note:** After disabling Kernel DMA Protection, Docker Desktop should show **"Engine running"** in the bottom left.
> If it still fails, also check that **"Intel VT-x"** or **"AMD-V"** is set to **Enabled** in the same BIOS section.

---

### 0.4 — Verify Docker works

Once Docker Desktop shows **"Engine running"**, open PowerShell and run:

```powershell
docker version
docker compose version
```

Expected output:
```
Client: Docker Engine - Community
 Version: 29.x.x
...
Docker Compose version v2.x.x
```

If you see version numbers — Docker is ready. Move to Step 1.

---

## STEP 1 — Start Redis

Redis runs as a Docker container. The `compose.yml` at the root of the project defines it.

```powershell
# Start Redis in background (detached mode)
docker compose up -d redis

# Verify it's running
docker ps
```

Expected output from `docker ps`:
```
NAMES     STATUS
redis     Up X seconds
```

> Redis is now running at `localhost:6379`. It starts automatically every time you run `docker compose up -d redis`.
> To stop it: `docker compose down`

---

## STEP 2 — Verify Redis Python package is installed

The `redis` package is already in `requirements.txt` — installed automatically by `setup.ps1`.
Just verify it works:

```powershell
.venv\Scripts\python.exe -c "import redis; print('redis OK')"
```

If you see `redis OK` — move to Step 3. If you see an error, run:
```powershell
uv pip install -r requirements.txt
```

---

## STEP 3 — Create the agent file

```
Path: src/agents/async_agent.py
```

Leave it completely empty — we will fill it block by block in Learn Mode.

---

## STEP 4 — Build in Learn Mode

Type this in GitHub Copilot Chat:

```
Learn Mode — I want to build 13 Async Agent
```

Copilot will guide you block by block:
1. Docstring
2. Imports (asyncio, json, threading, time, uuid, redis)
3. Contract vars + Redis client + JOB_TTL
4. SYSTEM_PROMPT
5. State TypedDict
6. LLM instantiation
7. `async def _run_llm_async()` — uses `ainvoke()`
8. `def _run_in_thread()` — runs coroutine via `asyncio.run()`
9. `node_start()` — generates job_id, starts thread
10. `node_poll()` — reads from Redis
11. `node_webhook_demo()` — blocking 5s demo
12. `route()` + `build_graph()` + `run_agent()`

---

## STEP 5 — Test in Studio

```powershell
# Redis must be running (Step 1)
docker compose up -d redis

# Start Studio
.venv\Scripts\python.exe studio.py
```

Open **http://localhost:8000** → select **Async Agent**

### How to test in Studio

1. Make sure Redis is running: `docker compose up -d redis`
2. Run Studio: `python studio/studio.py`
3. Open **http://127.0.0.1:8000** in your browser
4. Select **Async Agent** from the dropdown
5. Send any message — the job starts immediately and the agent returns a **Job ID** in under 1 second
6. Poll the result by sending: `job:<paste-the-job-id-here>`
7. Or trigger a blocking webhook demo: `webhook:process quarterly report`

## Test Checklist

| # | Input | Expected output | Trace expected |
|---|---|---|---|
| 1 | `"Explain what ainvoke does in LangGraph"` | `"Job started..."` + Job ID returned in **< 1 second** | `node_exec` (START) → content contains `ainvoke() started in background thread` |
| 2 | `"job:<uuid_from_test1>"` (immediately, < 15s) | `"Still processing..."` | `node_exec` (POLL) → `status=running` |
| 3 | `"job:<uuid_from_test1>"` (after **20+ seconds**) | Full LLM response as plain text | `node_exec` (POLL) → `status=done` + LLM text in content |
| 4 | `"webhook:process quarterly report"` | `"Webhook activated — POST alert sent."` after **~5 seconds** | `node_exec` (WEBHOOK) → `node_exec` (WEBHOOK FIRED) — 2 entries, UI frozen during wait |
| 5 | `"job:00000000-0000-0000-0000-000000000000"` | `"Job not found in Redis — it may have expired (TTL: 1 hour)..."` | `node_exec` (POLL) → `not found in Redis` |

**Why test #1:** The non-blocking proof — response must arrive in under 1 second. If it takes longer, Redis is not running (`docker compose up -d redis`). Confirms `ainvoke()` fires in a background thread and `job_id` is returned immediately.

**Why test #2:** Confirms Redis holds `status=running` while the background thread is still executing. The same `job_id` is used for tests #2 and #3 — proving that polling reads **live state** from Redis between calls.

**Why test #3:** Confirms the job completes and `status=done` is set in Redis with the LLM result. The full response is returned without any prefix — raw result from the background thread.

**Why test #4:** The blocking contrast — the UI is **completely frozen for ~5 seconds** during webhook execution. This is the key educational point: compare with test #1 which returns in < 1 second. Demonstrates why `ainvoke()` is preferred in production.

**Why test #5:** Verifies Redis TTL handling — a non-existent or expired `job_id` returns a clear error message. Without this, the agent would raise a `KeyError` or crash on `None`.

---

## STEP 6 — Verify with Redis CLI

See what was saved in Redis after Test 1:

```powershell
# In Docker Desktop: Containers → redis → Exec tab → type: redis-cli
# Or from PowerShell:
docker exec redis redis-cli KEYS "*"
docker exec redis redis-cli GET <job_id_from_test1>
docker exec redis redis-cli TTL <job_id_from_test1>
```

Expected output from `GET`:
```json
{"status": "done", "result": "ainvoke() is the async version of invoke()..."}
```

`TTL` shows seconds remaining until the job expires (max 3600 = 1 hour).

---

## Concept map — blocking vs non-blocking

```
BLOCKING (bad in production):
  user sends message
  → LLM starts (15s)
  → UI frozen — user cannot do anything
  → LLM finishes
  → user sees result

NON-BLOCKING (this agent):
  user sends message
  → job_id returned immediately (< 1s)  ← user can do other things
  → LLM runs in background thread via ainvoke()
  → user polls with job:<id> any time
  → when done → Redis returns result

WEBHOOK (production alternative to polling):
  user sends message
  → job starts in background
  → when done → agent POSTs result to callback URL automatically
  → no polling needed — receiver gets notified
```

---

## Common mistakes

| Mistake | What happens | Fix |
|---|---|---|
| Redis not running | `ConnectionRefused` error on import | `docker compose up -d redis` |
| Poll too fast | `status=running` — LLM not done yet | Wait 20s and poll again |
| Wrong job_id | `status=not_found` | Copy exact UUID from submit response |
| `await` outside `async def` | `SyntaxError` | Only use `await` inside `async def` |
| `asyncio.run()` in main thread | `RuntimeError` — event loop already running | Only call `asyncio.run()` in the background thread |
