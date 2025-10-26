You hit the OS file-descriptor limit (“**Too many open files**”), which then crashed Tornado’s event loop. After the loop died, Streamlit tried to check it and raised “**RuntimeError: no running event loop**”. In short: too many sockets/files were left open at once (lots of students + streaming + repeated client creation) → the server ran out of FDs → loop collapsed.

Below is a pragmatic fix plan and concrete code changes.

---

# What’s causing the FD explosion

1. **Re-creating network clients**
   `OpenAI(...)` is constructed at import time *on every rerun*. Each instance holds an underlying HTTPX client/transport with open connections. Under load (many students) these accumulate.

2. **Streaming responses not explicitly closed**
   When streaming, if a rerun/interruption/exceptions happen, the stream/generator may not get cleaned up promptly, leaving sockets open.

3. **High concurrency + low OS limits**
   Each browser tab holds a WebSocket to Streamlit, plus connections to OpenAI & Supabase. With a class full of students, you can exceed the default `ulimit -n` (often ~1024).

---

# Quick mitigations (ops)

* **Raise the OS FD limit** on the host/container:

  * Bash (temporary, current shell):

    ```bash
    ulimit -n 8192
    ```
  * systemd service override (persistent):

    ```
    [Service]
    LimitNOFILE=8192
    ```

    then `systemctl daemon-reload && systemctl restart your-service`
  * Docker: run with `--ulimit nofile=8192:8192`.

These alone reduce the chance of a blow-up.

---

# Code changes (safe, incremental)

### 1) Make the OpenAI client a shared cached resource with sane connection limits

```python
# at top
import httpx

@st.cache_resource
def get_openai_client():
    # Keep the connection pool modest to avoid FD spikes.
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
    transport = httpx.HTTPTransport(retries=2)
    http_client = httpx.Client(limits=limits, transport=transport, timeout=30.0)
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=http_client)

# replace:
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# with:
client = get_openai_client()
```

Why: one shared HTTPX client across reruns/sessions reuses sockets and honors pool limits, instead of creating many.

---

### 2) Explicitly close the streaming response (and remove the artificial sleep)

Replace your streaming block with one that always closes the stream, even on errors. (Newer SDKs have a context-manager API. If yours doesn’t, use `try/finally`.)

```python
# --- before calling the API, optionally trim history to the last N turns (see step 3) ---

full_response = ""

try:
    stream = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0.2,
        stream=True,
    )
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                full_response += delta
                response_placeholder.markdown(full_response + "▋")
        # final render without the cursor
        response_placeholder.markdown(full_response)
finally:
    # make sure sockets are returned to the pool promptly
    close = getattr(stream, "close", None)
    if callable(close):
        close()
```

* **Remove `time.sleep(0.01)`**. It slows the loop and holds the socket open longer without benefit.
* The `finally` ensures the file descriptor is released even if Streamlit reruns/interrupts.

> If your SDK supports it, prefer:
>
> ```python
> with client.chat.completions.stream(model="gpt-4.1", messages=messages, temperature=0.2) as stream:
>     for event in stream:
>         ...
>     # stream auto-closes here
> ```
>
> (Keep your `response_placeholder` logic; just adapt the loop to the events API.)

---

### 3) Cap conversation length to avoid very long streams

Right before the API call, keep only the last K turns (plus system):

```python
# keep only last 8 exchanges (16 messages) to reduce work and duration
MAX_TURNS = 8
trimmed_messages = [{"role": "system", "content": system_prompt}]
# take from the end: user/assistant pairs
dialog = [m for m in st.session_state.messages][-2*MAX_TURNS:]
trimmed_messages.extend(dialog)

# then pass `trimmed_messages` to the API instead of `messages`
```

This reduces token count, speeds replies, and shortens how long each socket stays open.

---

### 4) Prevent server-wide stampedes (optional but helpful)

Use a small semaphore shared across sessions to limit concurrent generations:

```python
import threading

@st.cache_resource
def get_generation_guard(max_concurrent: int = 10):
    return threading.Semaphore(max_concurrent)

GEN_GUARD = get_generation_guard()

# When generating:
if not GEN_GUARD.acquire(blocking=False):
    st.warning("Der Server ist gerade ausgelastet. Bitte in ein paar Sekunden erneut senden.")
    st.stop()

try:
    # ... do the streaming call here ...
    pass
finally:
    GEN_GUARD.release()
```

Pick a `max_concurrent` your server can handle (start with 10–20).

---

### 5) Keep one Supabase client (you already do) and avoid over-polling

You’re already using `@st.cache_resource` for Supabase — good.
Also, `get_authenticated_supabase_client()` calls `supabase.auth.get_user()` frequently; that’s OK, but avoid calling it inside tight loops.

---

### 6) Minor Streamlit hygiene

* Image loads (logo) are fine; Streamlit caches file content.
* Your rerun usage is OK. Just ensure you don’t call `st.rerun()` inside an except block right after the stream starts; the `finally: stream.close()` above prevents leaks.

---

# Putting it together (minimal diff)

**Change 1 — OpenAI client (top of file):**

```python
import httpx

@st.cache_resource
def get_openai_client():
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
    transport = httpx.HTTPTransport(retries=2)
    http_client = httpx.Client(limits=limits, transport=transport, timeout=30.0)
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), http_client=http_client)

client = get_openai_client()
```

**Change 2 — Trim history + safe streaming (inside `show_main_app()`):**

```python
# Build trimmed messages
messages = [{"role": "system", "content": system_prompt}]
MAX_TURNS = 8
dialog = [m for m in st.session_state.messages][-2*MAX_TURNS:]
messages.extend(dialog)

full_response = ""
stream = None
try:
    stream = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0.2,
        stream=True
    )
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                full_response += delta
                response_placeholder.markdown(full_response + "▋")
        response_placeholder.markdown(full_response)
finally:
    if stream and hasattr(stream, "close"):
        stream.close()
```

**(Optional) Change 3 — Global concurrency guard:**

```python
@st.cache_resource
def get_generation_guard():  # pick a limit
    return threading.Semaphore(12)

GEN_GUARD = get_generation_guard()
# before the API call:
if not GEN_GUARD.acquire(blocking=False):
    st.warning("Der Server ist ausgelastet. Bitte kurz warten und erneut versuchen.")
    st.stop()
try:
    # streaming call
    ...
finally:
    GEN_GUARD.release()
```

---

# After you deploy

1. Raise `ulimit -n` as shown.
2. Redeploy with the code fixes.
3. Watch logs for any remaining `Too many open files`. If they persist under heavy load, lower `max_connections` in the HTTPX client further (e.g., 10) and/or reduce `max_concurrent` in the semaphore.

---

If you want, paste your requirements/lockfile and how you deploy (local, systemd, Docker, Streamlit Cloud), and I’ll tailor `ulimit` + service settings for that environment.
