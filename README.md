# clawhealth

Health data bridge for OpenClaw.

`clawhealth` is a small toolbox that pulls health and fitness data from
external providers (starting with Garmin) into a local, agent-friendly
format. The goal is to let your OpenClaw agents understand your daily
training load, sleep, and recovery trends, and offer grounded suggestions
based on real signals rather than guesswork.

> Status: bootstrap. Only the project skeleton and CLI entrypoint exist;
> actual provider integrations and summaries will be added in later
> iterations.

---

## Vision

- **Single health hub**: aggregate data from multiple providers
  (Garmin, Huami, Suunto, smart scales, etc.) behind a single CLI.
- **Local-first, privacy-aware**: raw data lives on your machine; agents
  consume only derived summaries (e.g. daily stats), not full raw
  timeseries unless you explicitly opt in.
- **OpenClaw-native**: outputs are designed to be easy to feed into
  OpenClaw prompts, daily summaries, and long-term planning workflows.

---

## Example CLI shape (planned)

```bash
# Sync Garmin data into a local cache
clawhealth garmin sync --since 2026-03-01

# Show a human/agent-friendly summary for a given day
clawhealth daily-summary --date 2026-03-02

# In the future: other providers
clawhealth huami sync
clawhealth suunto sync
```

---

## License

MIT © Ernest Yu
