# Contributing

Thank you for improving these skills.

## Good contributions

- A concrete prompt where a skill triggers incorrectly or produces an unhelpful workflow.
- A reproducible script or validation improvement.
- A narrower rule supported by a real failure, not a universal rule inferred from one anecdote.
- Documentation that makes inputs, outputs, permissions, or uncertainty clearer.

## Pull request checklist

1. Keep the change inside one plugin unless the same invariant genuinely affects several plugins.
2. Use synthetic inputs. Never submit real birth data, financial details, chat exports, private project names, screenshots, credentials, or absolute home paths.
3. Run `powershell -ExecutionPolicy Bypass -File scripts/validate_repository.ps1`.
4. Explain what changed, why it helps, what was tested, and what remains unknown.
5. Confirm that new dependencies have a compatible license and are recorded in the relevant third-party notice.

Maintainers may ask for a smaller reproduction or reject changes whose privacy, provenance, or behavior cannot be reviewed.
