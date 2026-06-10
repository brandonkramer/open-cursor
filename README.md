# Opencursor

[![cursor-agent](https://badgen.net/static/cursor-agent/2026.06.04-5fd875e/gray)](https://cursor.com/cli)
[![@open-cursor/pi-agent](https://badgen.net/npm/v/@open-cursor/pi-agent?label=%40open-cursor%2Fpi-agent)](https://www.npmjs.com/package/@open-cursor/pi-agent)
[![@open-cursor/opencode-agent](https://badgen.net/npm/v/@open-cursor/opencode-agent?label=%40open-cursor%2Fopencode-agent)](https://www.npmjs.com/package/@open-cursor/opencode-agent)

Cursor Agent provider extension for [pi](https://github.com/badlogic/pi-mono).

Use Cursor's AI models directly from **pi** or **opencode** with your existing Cursor subscription. Supports Claude, GPT, Gemini, Grok, Composer, and Kimi models.

## Architecture

```
pi/opencode ──► opencursor ──► Cursor API (ConnectRPC/HTTP2)
                    │
                    ├── tool calls (read, write, bash, edit) ← relayed via tool-bridge
                    │
                    └── protobuf conversation state ← persisted to disk
```

## Protocol

Reverse-engineered Cursor agent protobuf protocol over ConnectRPC. Proto definitions in `proto/`, generated TypeScript in `packages/protocol/src/__generated__/`.

### Detect Drift

```sh
python3 scripts/diff-protocol.py          # exits 1 if gaps found
python3 scripts/extract-models.py         # check version + model count
python3 scripts/diff-protos.py            # field-level drift
```

## Credits & Sources

- [Jordan-Jarvis/cursor-grpc](https://github.com/Jordan-Jarvis/cursor-grpc) — RE'd proto files from Cursor IDE
- [eisbaw/cursor_api_demo](https://github.com/eisbaw/cursor_api_demo) — Python-based Cursor API RE toolkit
- [sudosubin/pi-frontier](https://github.com/sudosubin/pi-frontier) — Original pi-cursor-agent implementation and upstream

## Packages

| Package | Purpose |
|---|---|
| [`@open-cursor/pi-agent`](integrations/pi-agent/README.md) | Pi provider extension |
| `@open-cursor/opencode-agent` | Opencode provider extension |
| [`@open-cursor/protocol`](shared/protocol/README.md) | Proto definitions, generated types, RPC clients |
| [`@open-cursor/client`](shared/client/README.md) | Cursor protocol client, executors, auth |

## Models

| Canonical ID | Model | Thinking |
|---|---|---|
| `claude-sonnet-4-0` | Claude 4 Sonnet | off / thinking |
| `claude-sonnet-4-5` | Claude 4.5 Sonnet | off / thinking |
| `claude-sonnet-4-1m` | Claude 4 Sonnet 1M | off / thinking |
| `claude-sonnet-4-6` | Claude 4.6 Sonnet | off / thinking |
| `claude-opus-4-5` | Claude 4.5 Opus | off / thinking |
| `claude-opus-4-6` | Claude 4.6 Opus | off / thinking |
| `claude-opus-4-6-fast` | Claude 4.6 Opus (fast) | off / thinking |
| `claude-opus-4-6-max` | Claude 4.6 Opus Max | off / thinking |
| `claude-opus-4-6-max-fast` | Claude 4.6 Opus Max (fast) | off / thinking |
| `claude-opus-4-7` | Claude Opus 4.7 | high / max |
| `claude-opus-4-7-fast` | Claude Opus 4.7 (fast) | high / max |
| `claude-opus-4-7-max` | Claude Opus 4.7 Max | high / max |
| `claude-opus-4-7-max-fast` | Claude Opus 4.7 Max (fast) | high / max |
| `claude-opus-4-8` | Claude Opus 4.8 | medium / high / max |
| `claude-opus-4-8-fast` | Claude Opus 4.8 (fast) | medium / high / xhigh |
| `claude-opus-4-8-max` | Claude Opus 4.8 Max | medium / high / max |
| `claude-opus-4-8-max-fast` | Claude Opus 4.8 Max (fast) | medium / high / max |
| `claude-fable-5` | Claude Fable 5 | off → max (6 levels) |
| `composer-1.5` | Composer 1.5 | — |
| `composer-2` | Composer 2 | — |
| `composer-2-fast` | Composer 2 Fast | — |
| `composer-2.5` | Composer 2.5 | — |
| `composer-2.5-fast` | Composer 2.5 Fast | — |
| `gpt-5-mini` | GPT-5 Mini | — |
| `gpt-5.1` | GPT-5.1 | low / high |
| `gpt-5.1-codex-mini` | GPT-5.1 Codex Mini | low / high |
| `gpt-5.1-codex-max` | GPT-5.1 Codex Max | low → xhigh (5 levels) |
| `gpt-5.1-codex-max-fast` | GPT-5.1 Codex Max Fast | low → xhigh (5 levels) |
| `gpt-5.2` | GPT-5.2 | low → xhigh (4 levels) |
| `gpt-5.2-fast` | GPT-5.2 Fast | low → xhigh (4 levels) |
| `gpt-5.2-codex` | GPT-5.2 Codex | low → xhigh (4 levels) |
| `gpt-5.2-codex-fast` | GPT-5.2 Codex Fast | low → xhigh (4 levels) |
| `gpt-5.3-codex` | GPT-5.3 Codex | low → xhigh (4 levels) |
| `gpt-5.3-codex-fast` | GPT-5.3 Codex Fast | low → xhigh (4 levels) |
| `gpt-5.3-codex-spark` | GPT-5.3 Codex Spark | low → xhigh (4 levels) |
| `gpt-5.4` | GPT-5.4 | low → xhigh (5 levels) |
| `gpt-5.4-fast` | GPT-5.4 Fast | low → xhigh (4 levels) |
| `gpt-5.4-mini` | GPT-5.4 Mini | off → xhigh (6 levels) |
| `gpt-5.4-nano` | GPT-5.4 Nano | off → xhigh (6 levels) |
| `gpt-5.4-pro` | GPT-5.4 Pro | low → xhigh (5 levels) |
| `gpt-5.4-pro-fast` | GPT-5.4 Pro Fast | low → xhigh (4 levels) |
| `gpt-5.5` | GPT-5.5 | medium / high / xhigh |
| `gpt-5.5-pro` | GPT-5.5 Pro | medium / high / xhigh |
| `gpt-5.5-fast` | GPT-5.5 Fast | high / xhigh |
| `gemini-3-pro-preview` | Gemini 3 Pro | — |
| `gemini-3-flash-preview` | Gemini 3 Flash | — |
| `gemini-3.1-pro-preview` | Gemini 3.1 Pro | — |
| `gemini-3.5-pro-preview` | Gemini 3.5 Pro | — |
| `gemini-3.5-flash-preview` | Gemini 3.5 Flash | — |
| `grok-4.20-0309-non-reasoning` | Grok 4.20 | — |
| `grok-4.20-0309-reasoning` | Grok 4.20 (reasoning) | — |
| `grok-4.3` | Grok 4.3 | — |
| `grok-build-0.1` | Grok Build 0.1 | — |
| `kimi-k2.5` | Kimi K2.5 | — |

> Cursor exposes 141+ model variants. Run `cursor agent models` for the authoritative list.

## Development

```sh
npm run lint              # oxlint .
npm run format            # oxfmt .
npm run typecheck         # tsc --noEmit
npm run test              # tsx --test
npm run proto:generate    # buf generate
```

## Requirements

- `pi >= 0.74.0`
- Cursor subscription

## License

MIT
