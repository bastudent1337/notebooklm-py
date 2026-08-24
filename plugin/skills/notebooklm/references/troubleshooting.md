# Troubleshooting Reference

Part of the `notebooklm` skill. Error-handling decision tree, exit codes,
known limitations, and the `--help` map. See [SKILL.md](../SKILL.md) for the
condensed exit-code table used day-to-day.

## Error Handling

**On failure, offer the user a choice:**
1. Retry the operation
2. Skip and continue with something else
3. Investigate the error

**Error decision tree:**

| Error | Cause | Action |
|-------|-------|--------|
| Auth/cookie error | Session expired | Run `notebooklm auth check` then `notebooklm login` |
| "No notebook context" | Context not set | Use `-n <id>` or `--notebook <id>` flag (parallel), or `notebooklm use <id>` (single-agent) |
| "No result found for RPC ID" | Rate limiting | Wait 5-10 min, retry |
| `GENERATION_FAILED` | Google rate limit | Wait and retry later |
| Download fails | Generation incomplete | Check `artifact list` for status |
| Invalid notebook/source ID | Wrong ID | Run `notebooklm list` to verify |
| RPC protocol error | Google changed APIs | May need CLI update |

## Login Flow Quirks

Two `notebooklm login` failure modes look alarming but have quick, known fixes.

**"The browser window was closed during login" on the first attempt(s), even with a real display available.**
This is the same message a genuinely headless/no-display environment produces when Playwright can't render
a window at all, so the text alone doesn't tell you which case you're in. Disambiguate by elapsed time and
profile activity: a true no-display failure returns almost instantly, while a window that opened and was
then closed (by the person signing in, or by clicking away before it auto-closed) typically shows 1-3
minutes of "Waiting for login" first, and leaves real activity in `<profile>/browser_profile/Default`
(check the `Last Version` / `Local State` file mtimes — if they moved, a browser really did run). If still
ambiguous, just ask whoever is signing in whether a Chromium window actually appeared on their screen.
**Fix:** re-run `notebooklm login` (no flags needed — `--fresh` is only for actually-corrupted profiles) and
stay with the window until it closes itself; closing it early is the single most common cause of this error.

**First successful login (`Login detected.`) still fails `auth check` / `auth refresh` with
`Missing required cookies: __Secure-1PSIDTS`.** Google does not always mint the `__Secure-1PSIDTS`
security-token cookie on the very first sign-in into a fresh or freshly-cleared browser profile — every
other cookie (`SID`, `__Secure-1PSID`, etc.) is captured correctly, but this one token is sometimes only
issued on a subsequent authenticated visit. `auth refresh` cannot repair this itself, since its server-side
refresh needs that cookie to already be present. **Fix:** simply run `notebooklm login` again. The
persistent browser profile now already holds a valid Google session, so the second run is fast (often
resolves in under a minute) and reliably picks up the missing cookie. Confirm with
`notebooklm auth check --test --json` — require `"status": "ok"` and `"checks": {"token_fetch": true}`
with no `error` under `details`.

## Exit Codes

All commands use consistent exit codes:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Continue |
| 1 | Error (not found, processing failed, validation, auth, rate limit) | Check stderr, see Error Handling |
| 2 | Timeout (wait commands) or unexpected/system error | Extend timeout, check status manually, or report a bug |
| 130 | Cancelled by user (SIGINT / Ctrl-C) | `128 + signal 2`; the process was interrupted, not a failure |

**Examples:**
- `source wait` returns 1 if source not found or processing failed
- `artifact wait` returns 2 if timeout reached before completion
- `generate` returns 1 if rate limited (check stderr for details)
- Pressing Ctrl-C during any command returns 130

Full policy, the exception → exit-code mapping, and the `--json` error
envelope shape: [docs/cli-exit-codes.md](https://github.com/teng-lin/notebooklm-py/blob/main/docs/cli-exit-codes.md).

## Known Limitations

**Rate limiting:** Audio, video, quiz, flashcards, infographic, and slide deck generation may fail due to Google's rate limits. This is an API limitation, not a bug.

**Reliable operations:** These always work:
- Notebooks (list, create, delete, rename)
- Sources (add, list, delete)
- Chat/queries
- Mind-map, study-guide, report, data-table generation

**Unreliable operations:** These may fail with rate limiting:
- Audio (podcast) generation
- Video generation
- Quiz and flashcard generation
- Infographic and slide deck generation

**Workaround:** If generation fails:
1. Check status: `notebooklm artifact list`
2. Retry after 5-10 minutes
3. Use the NotebookLM web UI as fallback

**Polling intervals:** When checking status manually, poll every 15-30 seconds to avoid excessive API calls.

## Troubleshooting

```bash
notebooklm --help              # Main commands
notebooklm auth check          # Diagnose auth issues
notebooklm auth check --test   # Full auth validation with network test
notebooklm source --help       # Source management
notebooklm research --help     # Research status/wait/cancel
notebooklm generate --help     # Content generation
notebooklm artifact --help     # Artifact management
notebooklm download --help     # Download content
notebooklm language --help     # Language settings
```

**Diagnose auth:** `notebooklm auth check` - shows cookie domains, storage path, validation status
**Re-authenticate:** `notebooklm login`
**Check version:** `notebooklm --version`
**Refresh a CLI-managed install:** `notebooklm skill install`
