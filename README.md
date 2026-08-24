# Evidence-first Codex skills

Three independent, privacy-scrubbed Codex plugins built around evidence, explicit uncertainty, and reviewable workflows.

| Plugin | Purpose | Extra setup |
| --- | --- | --- |
| `duo-dept-pipeline` | Commercial content validation and film-previsualization workflow | Optional Tencent Hunyuan3D credentials for its API helper |
| `life-opportunity-radar` | Current-source opportunity research with falsifiers and entry-gate analysis | Add your own local strategy profile if you want personalized scoring |
| `bazi-ziwei-reading` | Script-calculated Bazi and Ziwei charts with traditional interpretation boundaries | Run its dependency setup script once |

## Install from a clone

Clone this repository, then register its local marketplace root:

```powershell
codex plugin marketplace add <path-to-this-repository>
codex plugin add duo-dept-pipeline@evidence-first-skills
codex plugin add life-opportunity-radar@evidence-first-skills
codex plugin add bazi-ziwei-reading@evidence-first-skills
```

Install only the plugins you need. Start a new Codex task after installation so the new skills are discovered.

The standalone skill folders also follow the open agent-skills layout and can be installed from this repository with Codex's `$skill-installer`.

## Privacy boundary

This repository is a public edition, not a mirror of any maintainer's installed skill directory. It intentionally excludes personal strategy profiles, conversation extracts, client birth data, local test results, absolute home paths, credential files, generated media, and private project evidence.

Before every commit, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_repository.ps1
```

The scan is a guardrail, not proof of anonymity. Review diffs semantically before publishing. See [PRIVACY.md](PRIVACY.md).

## Contributing

Issues and pull requests are welcome. Please describe the failure or use case, keep changes scoped, and include a reproducible check where practical. Do not include real personal data in prompts, fixtures, screenshots, logs, or chart examples. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Original repository content is available under the MIT License. Third-party runtime dependencies keep their own licenses and are not vendored in this repository.
