# AGENTS.md — opencursor

Practices, technicals, bugs, issues, fixes. For overview, see [README.md](./README.md) and package-level READMEs.

## Proto System

```
proto/agent/v1/*.proto ──► buf generate ──► shared/protocol/src/__generated__/
```

Config: `shared/protocol/buf.gen.yaml`. Client version: `shared/protocol/src/constants.ts` (`CURSOR_CLIENT_VERSION` — keep in sync with installed `cursor-agent`).

Two services: **`AgentService.Run`** (bidirectional stream) and **`AiService.GetUsableModels`** (unary).

### Drift Detection

```sh
python3 scripts/diff-protocol.py          # exits 1 if crash-risk gaps
python3 scripts/diff-protos.py            # field-level drift
python3 scripts/extract-models.py         # version + model count
```

Run after every `cursor-agent` update. `diff-protocol.py` checks 11 core types (AgentServerMessage, AgentClientMessage, InteractionUpdate, etc.).

### Safety net

`shared/protocol/src/agent.ts` has `wrapParseErrorSafe()` — catches `"parse binary"` + `"illegal tag"` errors and converts to clean end-of-stream. Prevents proto drift from crashing sessions.

## Model Mapping

`integrations/pi-agent/src/models/mapping.ts` / `integrations/opencode-agent/src/models/mapping.ts`

1. **`default` must be non-thinking** — mapping to `-thinking-*` forces thinking even when disabled, causing rejections.
2. **Each thinking level gets a distinct variant** — `none`/`minimal`/`low`/`medium`/`high`/`xhigh`.
3. **`toCanonicalId()` filters** — only `default` mapping creates a canonical entry. Variant models return `null` and are hidden from the model list.
4. **Verify against `cursor agent models`** — naming conventions vary by family.

## Known Issues & Fixes

- **Fable 5 privacy policy** — silent failure. Requires accepting data retention at [cursor.com/settings](https://cursor.com/settings).
- **Proto drift kills sessions silently** — wrong field definitions cause `illegal tag: field no N wire type 7` parse errors. Always run `diff-protocol.py` after updates.
- **`TrackedGitRepoBranches` was wrong** — defined as `map<string, string>` but server sends `{repo_path, branch_name}`. Fixed in `agent.proto` field 1/2.
- **`TurnEndedUpdate` was empty** — server sends `input_tokens/output_tokens/cache_read_tokens/cache_write_tokens`. Added `optional int64` fields + wired through `interaction-conversion.ts` + accumulated in `stream.ts`.
- **Git status was removed for perf** — `getGitStatus()` called `git status --porcelain` with 5s timeout every turn. Removed; `status: ""` is always sent.

## Constraints

- **No generated file edits** — `__generated__/` is `buf generate` output. Change `proto/*.proto` then regenerate.
- **No `as any` / `oxlint-disable` without inline reason** — strict TypeScript.
- **Cursor-native tools excluded from MCP** — `bash, read, write, delete, ls, grep, lsp, todo_write` handled at exec protocol level.
- **Dangerous shell guard** — `sudo`, `rm -rf`, `shutdown`, `curl|sh` trigger UI confirmation.
- **Vendored code is fragile** — `shared/client/src/vendor/` extracted from Cursor's JS bundle. Re-extract on protocol changes.
- **Pi stays orchestrator** — Cursor never touches filesystem. All tool execution relays back to host.

## Commands

```sh
npm run lint              # oxlint .
npm run format            # oxfmt .
npm run typecheck         # tsc --noEmit
npm run test              # tsx --test
npm run proto:generate    # buf generate
```
