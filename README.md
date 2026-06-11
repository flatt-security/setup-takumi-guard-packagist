<p align="center">
  <img src="branding.png" alt="Takumi Guard — a panda security guard scanning Composer packages" width="300" />
</p>

<h1 align="center">Takumi Guard for Packagist</h1>

<p align="center">
  <strong>Stop malicious Composer packages before they reach your CI.</strong><br />
  A GitHub Action that routes <code>composer install</code> through a security proxy — no secrets, no config files, two lines of YAML.
</p>

<p align="center">
  <a href="https://github.com/flatt-security/setup-takumi-guard-packagist/actions/workflows/test.yml"><img src="https://github.com/flatt-security/setup-takumi-guard-packagist/actions/workflows/test.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/flatt-security/setup-takumi-guard-packagist" alt="License" /></a>
</p>

---

> **Not using CI?** For local setup on your laptop, see the [email registration & token management appendix](#appendix-email-registration--token-management) below.

## Contents

- [What is Takumi Guard?](#what-is-takumi-guard)
- [Quickstart (3 steps)](#quickstart)
- [Setup modes](#setup-modes)
- [Adopting Takumi Guard](#adopting-takumi-guard)
- [Inputs](#inputs)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Appendix: Email registration & token management](#appendix-email-registration--token-management)

---

## What is Takumi Guard?

Every `composer install` in your CI is a trust decision. Takumi Guard sits between your workflow and Packagist, **blocking known-malicious packages before they execute**.

- **How it works** -- Routes package metadata through a security proxy (`packagist.flatt.tech`) that checks packages against a threat database in real time.
- **What you change** -- One step in your workflow YAML. No `composer.json` edits, no secrets to manage.
- **What it supports** -- **Composer 2.x**. Speaks the Composer repository protocol.

---

## Quickstart

**Goal:** Add Takumi Guard to any GitHub Actions workflow. No account required.

**Step 1.** Add the action to your workflow file (e.g. `.github/workflows/ci.yml`):

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: shivammathur/setup-php@v2
    with:
      php-version: '8.3'
      tools: composer:v2

  - uses: flatt-security/setup-takumi-guard-packagist@v1   # <-- add this line

  - run: composer install
  - run: composer test
```

> **Ordering:** Put this action *before* `composer install` or anything that triggers it. It configures the global Composer repository and (optionally) writes `COMPOSER_AUTH` — both need to be in place before any package fetch happens.

**Step 2.** Push the change. Every package fetch in this job now runs through the Takumi Guard proxy. Malicious packages are blocked automatically.

**Step 3.** *(Optional)* **Want audit logging and a dashboard?** Add a Bot ID for full visibility into package activity:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # Required for authentication
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          tools: composer:v2

      - uses: flatt-security/setup-takumi-guard-packagist@v1
        with:
          bot-id: "YOUR_BOT_ID"

      - run: composer install
```

> **Where do I get a Bot ID?** Create one at [Shisho Cloud byGMO](https://cloud.shisho.dev) -- or skip this entirely. Blocking works without it. The Bot ID is a public reference key, not a secret.

---

## Setup modes

| Mode | Blocks malware | Audit logging | Account needed | Best for |
|---|:---:|:---:|:---:|---|
| **[Blocking only](#blocking-only)** | Yes | No | No | OSS projects, quick evaluation |
| **[Full protection](#full-protection)** | Yes | Yes | Yes | Production workloads |
| **[Auth-only](#auth-only-advanced)** | You manage | Yes | Yes | Custom Composer setups |

---

### Blocking only

> **No account needed.** Add one line and you are protected.

Blocks known-malicious packages. No signup, no authentication.

```yaml
- uses: flatt-security/setup-takumi-guard-packagist@v1
```

Good for open-source projects or quick evaluation.

---

### Full protection

> **Recommended for production.** Blocks threats _and_ logs all package activity to your dashboard.

```yaml
permissions:
  id-token: write

steps:
  - uses: flatt-security/setup-takumi-guard-packagist@v1
    with:
      bot-id: "YOUR_BOT_ID"
```

**Key details:**
- Auth is handled via **GitHub's built-in OIDC** -- no PATs or secrets to rotate.
- The action does a one-shot OIDC → STS exchange at job start, writes the resulting short-lived JWT to `COMPOSER_AUTH` in `$GITHUB_ENV`, and Composer Basic-auths every request to the proxy for the rest of the job.
- If authentication fails (invalid `bot-id`, missing OIDC permission, STS unreachable, transient upstream error), the action exits with a clear error message and the build fails. There is no silent fallback to blocking-only mode.
- Get a Bot ID from [Shisho Cloud byGMO](https://cloud.shisho.dev).

---

### Auth-only (advanced)

> **For custom setups.** You manage the Composer repository yourself. The action only handles authentication (writing `COMPOSER_AUTH`).

```yaml
- uses: flatt-security/setup-takumi-guard-packagist@v1
  with:
    bot-id: "YOUR_BOT_ID"
    set-repository: false
```

**Key details:**
- Useful for projects that need full control over Composer repository configuration (e.g. a committed `composer.json` with a custom `repositories` block).
- You must configure the repository yourself, e.g. in `composer.json`:
  ```json
  {
    "repositories": [
      {"type": "composer", "url": "https://packagist.flatt.tech"},
      {"packagist.org": false}
    ]
  }
  ```
- If authentication fails, **the action exits with an error** -- there is no fallback.

---

## Adopting Takumi Guard

**Blocking works immediately — no lockfile changes needed.** The action configures a global Composer `composer`-type repository at `packagist.flatt.tech` and disables `packagist.org`. On **Composer 2.10+**, the proxy's dependency-policy filter blocks malicious packages during `composer install` and `composer update`, **including installs from an existing, unmodified `composer.lock`**. Older Composer versions block during `composer update` / `composer require` only.

**For projects with private packages:** Private Composer repositories (e.g. `satis`, Private Packagist, VCS sources) declared in `composer.json` under `repositories` are unaffected — they resolve directly. The action only redirects the default `packagist.org` source.

**For projects with vendored dependencies:** Nothing to do. `composer install --no-dev` with a committed `vendor/` reads from the local copy and never hits the network.

> **Optional — download tracking.** Composer embeds each package's download URL in `composer.lock`. To route downloads through the proxy (so installs are tracked and breach notifications cover the exact versions you ran), run `composer update mirrors` once and commit the result — it rewrites only the lock's download URLs, not package versions. This is **not required for blocking**; it accrues automatically the next time you `composer update`.

> **No packagist.org fallback.** The action disables `packagist.org` as a source. If the Guard proxy returns an error for a package, Composer will not silently fall back to fetching it directly from `packagist.org` — this is intentional to preserve the blocklist guarantee.

---

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `bot-id` | No | -- | Bot ID from Shisho Cloud byGMO. Omit for blocking-only mode. |
| `set-repository` | No | `true` | Configure the global Composer repository and disable packagist.org. Set to `false` if you manage repositories yourself. |
| `fail-closed` | No | `false` | Set `policy.ignore-unreachable=false` so `composer install`/`update` **fail** if the Guard proxy is unreachable, instead of proceeding unblocked. Recommended for CI that must never install while the proxy is down. Composer 2.10+. |
| `registry-url` | No | `https://packagist.flatt.tech` | Registry endpoint (must speak the Composer repository protocol). |
| `sts-url` | No | `https://sts.cloud.shisho.dev` | STS endpoint for token exchange. |
| `expires-in` | No | `1800` | Token lifetime in seconds (max 86400). |

---

## Outputs

| Output | Description |
|---|---|
| `token-expires-at` | ISO 8601 timestamp of token expiration. Only set when authenticated. |

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `OIDC not available` | Missing permission on the job | Add `permissions: { id-token: write }` to your job |
| `STS returned non-JSON (HTTP N)` | An error response from STS or an upstream layer was not valid JSON (e.g. an HTML error page from a transient outage) | Usually a transient infrastructure issue. The HTTP status and a body snippet are echoed to the log to help diagnose. |
| `STS returned HTTP N without an access_token` | STS rejected the auth request | The job log includes STS's own message inside this error. Common cases: `invalid ID token` -- trust condition mismatch, check the bot's trust settings in Shisho Cloud byGMO; `invalid request` -- malformed bot-id, double-check the value from your console. |
| `GitHub OIDC token fetch failed` | Could not reach `token.actions.githubusercontent.com` or got a non-200 response | Usually transient; the action retries up to 3 times. Persistent failures point at a GitHub Actions issue. |
| `composer: command not found` | PHP/Composer not installed before this action | Add `shivammathur/setup-php@v2` before `setup-takumi-guard-packagist` |
| `... was flagged as malware` / resolution fails for a specific package | The package (or the locked version) is on the blocklist — this is the proxy working | Use a non-blocked version. To inspect, run `composer audit --locked`. |
| `Package X not found` after enabling | A private package is resolving through the proxy instead of its own repository | Declare the private package as its own `vcs`/`path`/`satis` repository in `composer.json` (see Adopting Takumi Guard) |
| Build silently fetches from packagist.org | `set-repository: false` without configuring the repository in `composer.json` | Either remove `set-repository: false` or add the `repositories` block to `composer.json` yourself |

> **Still stuck?** Open an issue on this repository with your error output and workflow file (redact any IDs).

---

## Security

- **Short-lived tokens** -- 30 minutes by default, 24 hours max.
- **Auto-masked** -- Access tokens are automatically masked in workflow logs.
- **Job-scoped `COMPOSER_AUTH`** -- The action writes `COMPOSER_AUTH` to `$GITHUB_ENV` on the ephemeral runner. The token is never written to any file tracked by git.
- **Basic auth over HTTPS** -- Composer sends `Authorization: Basic <base64(_:JWT)>` to `packagist.flatt.tech`. The JWT is never written to any file tracked by git.
- **No direct packagist.org fallback** -- `packagist.org` is disabled as a Composer source. Packages can only be fetched through the proxy.

---

## Appendix: Email registration & token management

> **Optional.** Register your email to receive breach notifications if a package you installed is later flagged as malicious. This works for local development -- CI workflows should use [Full protection](#full-protection) instead.

### Register

```bash
curl -X POST https://packagist.flatt.tech/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

Check your inbox and click the verification link. You will receive a token like `tg_anon_xxx...`.

**Language preference:** Add `"language": "ja"` to receive emails in Japanese. Defaults to English (`"en"`) if omitted.

```bash
curl -X POST https://packagist.flatt.tech/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "language": "ja"}'
```

> **Reusing an existing token:** If you have already registered with Takumi Guard for npm, PyPI, Go, or RubyGems, the same `tg_anon_*` token works here -- it is a universal key across all ecosystems.

### Configure Composer

Set up the global repository and attach your token:

```bash
# 1. Route package fetches through Takumi Guard.
composer config --global repositories.packagist composer https://packagist.flatt.tech
composer config --global repositories.packagist.org false

# 2. Attach your token (Composer reads COMPOSER_AUTH for HTTP Basic credentials).
export COMPOSER_AUTH='{"http-basic": {"packagist.flatt.tech": {"username": "_", "password": "tg_anon_xxx..."}}}'
```

To make `COMPOSER_AUTH` permanent, add the `export` line to your shell profile.

After this, every `composer install` and `composer require` routes through Takumi Guard with your identity attached. If a package you downloaded is later found to be malicious, you will receive a breach notification email.

### Check token status

```bash
curl -H "Authorization: Bearer tg_anon_xxx..." \
  https://packagist.flatt.tech/api/v1/tokens/status
```

### Rotate your key

```bash
curl -X POST -H "Authorization: Bearer tg_anon_xxx..." \
  https://packagist.flatt.tech/api/v1/tokens/regenerate
```

Returns a new API key. The old one is invalidated immediately. Update your `COMPOSER_AUTH` with the new key.

### Revoke a token

```bash
curl -X DELETE -H "Authorization: Bearer tg_anon_xxx..." \
  https://packagist.flatt.tech/api/v1/tokens
```

---

<p align="center">
  Built by <a href="https://flatt.tech">GMO Flatt Security Inc.</a><br />
  <a href="LICENSE">MIT License</a>
</p>
