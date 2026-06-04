---
name: full-release
description: Run the complete cross-platform E-Tipitaka release end to end — build the Windows .exe and Linux binary on CI, build + sign + notarize both macOS .app (arm64 + Intel), package all four into versioned .zip files, and publish through the website release flow. Use whenever the user wants to "do a full release", "release version X", "ship all platforms", "release everything", or invokes /full-release. ALWAYS confirm the changelog with the user and report a pre-flight summary before the real (production) release step — never publish without that confirmation.
---

# Full release (all platforms)

Take the current committed state and ship it to every platform + the website.
This orchestrates several already-proven pieces; prefer the bundled scripts over
re-deriving steps. Two hard human gates are non-negotiable (the user asked for
them explicitly): **confirm the changelog** and **report a summary + get
confirmation before the real release**.

Repos involved:
- Desktop app (this repo): `/Volumes/SeagateBackup/Works/watnapahpong/E-Tipitaka-PC`
- Website: `/Volumes/SeagateBackup/Works/watnapahpong/etipitaka_web/etipitaka-docker` (`scripts/release.sh`, `versions/`)

GitLab project for CI: `sutee-s/e-tipitaka-pc` (API path `sutee-s%2Fe-tipitaka-pc`).

## Step 0 — Preconditions

- Be on `master` with the release commit merged. Confirm the version: read
  `settings.py` (`VERSION`). It must also match `etipitaka.spec`
  (`CFBundleShortVersionString` / `CFBundleVersion`). If the user wants a new
  version, bump those first (see how 3.2.1 was bumped) — don't release a number
  that's already live.
- macOS signing prereqs ready (see the `release-mac` skill): `.venv` (arm64),
  `.venv-x86` (universal2), Developer ID cert, notarytool profile
  `etipitaka-notary`.
- Set `VER` (from settings.py) and `WEB=/Volumes/SeagateBackup/Works/watnapahpong/etipitaka_web/etipitaka-docker`.

## Step 1 — Build Windows + Linux on CI

The `build:windows` and `build:linux` jobs are manual. Trigger a pipeline on
master and play them, capturing the job IDs (needed for packaging):

```bash
R=sutee-s/e-tipitaka-pc; RA=sutee-s%2Fe-tipitaka-pc
PIPE=$(glab ci run -b master -R "$R" | grep -oE 'id: [0-9]+' | grep -oE '[0-9]+')
sleep 6
WIN_JOB=$(glab ci get -p "$PIPE" -R "$R" --with-job-details | awk '/build:windows/{print $1; exit}')
LIN_JOB=$(glab ci get -p "$PIPE" -R "$R" --with-job-details | awk '/build:linux/{print $1; exit}')
glab api --method POST "projects/$RA/jobs/$WIN_JOB/play"
glab api --method POST "projects/$RA/jobs/$LIN_JOB/play"
```

Then poll both jobs until `success` (use a capped background loop — windows
~18 min, linux ~7 min). Record `$WIN_JOB` and `$LIN_JOB`. If either fails,
fetch the trace (`glab ci trace <job> -R $R`) and stop.

## Step 2 — Build + sign + notarize macOS

Run in the background (~20–40 min incl. Apple notarization):

```bash
./packaging/macos/release_mac.sh
```

This builds both `.app`, Developer ID signs (hardened runtime), notarizes, and
staples — producing `dist/E-Tipitaka-arm64.app` and `dist/E-Tipitaka-x86_64.app`.
This is exactly the `release-mac` skill; if it errors, debug there.

Steps 1 and 2 are independent — start both and let them run concurrently.

## Step 3 — Package all four into versioned zips

Once CI is green and the mac apps are notarized:

```bash
./packaging/release/make_release_zips.sh "$VER" "$WEB" "$WIN_JOB" "$LIN_JOB"
```

Produces in `$WEB/versions/$VER/`:
`E-Tipitaka-$VER-{arm64,x86_64,windows-x86_64,linux-x86_64}.zip`. It verifies
each mac bundle is signed + stapled and uses `ditto` so notarization survives
zipping. Spot-check one mac zip:
`ditto -x -k <zip> /tmp/chk && spctl -a -vv -t exec /tmp/chk/E-Tipitaka.app`
→ expect `accepted · source=Notarized Developer ID`.

## Step 4 — GATE: confirm the changelog

`$WEB/versions/$VER/changelog.md` drives the website "what's new" + the release
record. **Always** show its contents to the user and ask them to confirm or
edit before going further. If it's missing, draft a short Thai changelog from
the actual changes in this release and ask the user to approve. Do not skip
this — publishing a wrong/empty changelog is user-visible and hard to walk back.

## Step 5 — GATE: dry-run + summary, then confirm

Run the website dry-run (no side effects) and report a concise summary to the
user — version, the four files + sizes, the download URLs, and what the real
run will change (archive prior release, upload, update prod DB, refresh
manifest):

```bash
cd "$WEB" && ./scripts/release.sh --dry-run
```

Then **ask the user to confirm** before the real release. Only proceed on an
explicit yes.

## Step 6 — Real release

```bash
cd "$WEB" && ./scripts/release.sh --yes
```

It archives the prior release on the download host, uploads the 4 zips, 200-checks
them, publishes the static `etipitaka/latest.json`, updates the prod DB
(`update_release`: version + 4 URLs + changelog), and verifies the site.

## Step 7 — Verify live

```bash
curl -fsS https://etipitaka.com/api/version.json                       # endpoint
curl -fsS https://download.watnapahpong.org/data/etipitaka/latest.json  # static fallback
```

Both must report the new version with all four download URLs. Report success.

## Notes / failure handling

- `versions/*/` is gitignored — release artifacts never enter git.
- A normal direct-download release keeps the in-app updater ON. Do **not** use
  the Store toggle (`build.store.toml`) for this flow.
- If `release.sh` fails after uploading but before the site update, files are on
  the host but the DB is unchanged (broken-button safe state) — re-run once the
  cause is fixed; versioned filenames don't collide.
- The in-app updater on existing installs reads the manifest from Step 7, so a
  successful Step 6 is what actually notifies users.
