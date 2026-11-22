# Windows Test And Startup Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing 16-test suite deterministic, make dependency installation work under Chinese Windows locales, and allow the documented root-directory server startup command to work.

**Architecture:** Keep production cache behavior and dependency versions unchanged. Isolate the TTL test from global configuration, make the requirements file locale-independent, and resolve the logging configuration relative to its importing module.

**Tech Stack:** Python 3.12, pytest, pip 23.2, Flask, Redis, MySQL.

## Global Constraints

- Do not change cache TTL or jitter defaults.
- Do not change dependency names or pinned versions.
- Do not modify existing database data.
- Do not refactor unrelated authentication, Session, or deployment code.
- Verify before committing; push only the requested fix branch.

---

### Task 1: Deterministic TTL Test

**Files:**
- Modify: `tests/test_cache_utils.py:15-20`

**Interfaces:**
- Consumes: `cache_utils.cache_set(key, value, ttl)`, `cache_utils.config.CACHE_TTL_JITTER`.
- Produces: A test-local jitter value of 50, restored automatically by pytest.

- [ ] **Step 1: Reproduce the existing failure**

Run with Redis available:

```bash
python -m pytest tests/test_cache_utils.py::test_ttl_has_jitter -q
```

Expected before the fix: intermittent assertion failure when the configured 60-second jitter produces a TTL above 150.

- [ ] **Step 2: Apply the minimal test change**

```python
def test_ttl_has_jitter(monkeypatch):
    """TTL 必须落在 [基础值, 基础值+抖动上限] 区间内（防雪崩的核心保证）。"""
    base, jitter = 100, 50
    monkeypatch.setattr(cache_utils.config, 'CACHE_TTL_JITTER', jitter)
    cache_utils.cache_set('test:ttl', 'x', ttl=base)
    ttl = redis_client.ttl('test:ttl')
    assert base <= ttl <= base + jitter
```

- [ ] **Step 3: Verify the test repeatedly**

```bash
for i in {1..20}; do python -m pytest tests/test_cache_utils.py::test_ttl_has_jitter -q || exit 1; done
```

Expected: all 20 runs pass.

### Task 2: Locale-Independent Requirements File

**Files:**
- Modify: `requirements.txt:1-30`

**Interfaces:**
- Consumes: Existing pip requirement entries.
- Produces: Identical pinned requirements with ASCII-only comments.

- [ ] **Step 1: Reproduce the default-locale failure**

```bash
python -m pip install --dry-run --no-index -r requirements.txt
```

Expected before the fix on this machine: `UnicodeDecodeError` using `cp936`.

- [ ] **Step 2: Convert comments to ASCII**

Retain every requirement line unchanged; replace Chinese comments with equivalent English comments.

- [ ] **Step 3: Verify without UTF-8 overrides**

```bash
python -m pip install --dry-run --no-index -r requirements.txt
python -m pip check
```

Expected: all requirements already satisfied; no broken requirements.

### Task 3: Working-Directory-Independent Logging Configuration

**Files:**
- Modify: `Code/checkFunc.py:1-17`

**Interfaces:**
- Consumes: `Code/logging.conf` beside `checkFunc.py`.
- Produces: Successful logging initialization from either the repository root or `Code/`.

- [ ] **Step 1: Reproduce the root-directory startup failure**

```bash
python Code/start_server.py
```

Expected before the fix: `FileNotFoundError: logging.conf doesn't exist`.

- [ ] **Step 2: Resolve the configuration from the module path**

```python
import os
import logging
import logging.config

LOGGING_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(LOGGING_CONFIG)
logger = logging.getLogger('applog')
```

Keep the surrounding imports organized without changing any database or business function.

- [ ] **Step 3: Verify imports from both working directories**

```bash
cd /d/PythonProject/R_project
PYTHONPATH=Code python -c "import checkFunc; print('root import OK')"
cd /d/PythonProject/R_project/Code
python -c "import checkFunc; print('Code import OK')"
```

Expected: both commands print their success marker.

### Task 4: Full Regression And Runtime Verification

**Files:**
- Verify only; no additional production files.

**Interfaces:**
- Consumes: all changes above, local MySQL, local Redis, two Web instances.
- Produces: recorded test and runtime results suitable for the final report.

- [ ] **Step 1: Run the complete test suite**

```bash
python -m pytest tests -q
```

Expected: `16 passed`.

- [ ] **Step 2: Start two instances from the repository root**

Use the same test-only `SECRET_KEY` and ports 5000/5001; request `/`, `/login`, `/news_list`, and `/websocket` on each instance. Expected: HTTP 200.

- [ ] **Step 3: Verify cross-instance Session**

Read one existing student account without printing its `class` value, log in through port 5000, request `/aboutus` through port 5001 with the same cookie, and assert that the page contains that account's `uname`. Finish through `/login_out` to clean the test session.

- [ ] **Step 4: Inspect and commit the verified changes**

```bash
git diff --check
git status --short
git add Code/checkFunc.py requirements.txt tests/test_cache_utils.py docs/superpowers
git commit -m "fix: 修复 Windows 测试与启动兼容性"
```

Expected: only the scoped files are committed, with the required Claude attribution trailer.

- [ ] **Step 5: Push the fix branch**

```bash
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push -u origin fix/windows-test-startup
```

Expected: GitHub reports the new remote branch and upstream tracking is set.
