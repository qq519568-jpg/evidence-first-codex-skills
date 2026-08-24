# Privacy and publication policy

Public Git history is durable. Deleting a secret or personal record in a later commit does not make the earlier commit private.

## Never commit

- API keys, tokens, passwords, cookies, credential exports, `.env` files, or signed download URLs.
- Real names, email addresses, phone numbers, addresses, birth records, financial obligations, education history, health information, or personal strategy profiles.
- Chat transcripts, model session logs, browser profiles, generated-output directories, or private acceptance notes.
- Absolute user-home paths, machine-specific project roots, local backup paths, or internal asset locations.
- Third-party assets or datasets without verified redistribution rights.

## Safe test data

Use obviously synthetic names and inputs that were created for the test. Label examples as synthetic. Avoid recycling a maintainer's real values and merely calling them fictional.

## Reporting a leak

Do not open a public issue containing the sensitive value. Use GitHub's private vulnerability-reporting channel if it is enabled, or contact the repository owner privately through the account's published contact method. Include only the affected file and commit identifier; do not repeat the secret itself.

If a credential was exposed, removing it from Git is not enough: revoke or rotate it first, then rewrite repository history if needed.
