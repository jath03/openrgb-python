---
name: release
description: Cut a new openrgb-python release (version bump, release commit, annotated tag, push to trigger the PyPI publish workflow). Use when the user asks to release, publish, or cut a new version.
---

# Release openrgb-python

Releases follow a fixed pattern established by previous release commits and tags. Do not deviate from it.

## 1. Determine current state

```bash
git tag -l --sort=-v:refname | head -1        # latest tag, e.g. v0.3.7
grep "version=" setup.py                      # current version
git log --oneline <latest-tag>..HEAD          # changes to be released
```

If HEAD is not on `master`, or the tree is dirty, stop and ask the user.

## 2. Choose the new version

Following project history:

- **Patch bump** (0.3.6 → 0.3.7) for bugfixes, doc tweaks, CI/workflow fixes.
- **Minor bump** (0.2.15 → 0.3.0) for a batch of features or new SDK/plugin functionality.

Use semantic judgment based on the commits since the last tag. If it is ambiguous, ask the user.

## 3. Update the version

Edit `setup.py` — the only change in the release commit is the version string:

```python
version='X.Y.Z',
```

## 4. Create the release commit

Commit message is exactly the version, no prefix or body:

```bash
git add setup.py
git commit -m "vX.Y.Z"
```

## 5. Create the annotated tag

The tag message is a short human summary (one line) of what changed since the previous tag, e.g. `Mode validation improvements`, `SDK plugins and segments`. Derive it from the commits in step 1.

```bash
git tag -a vX.Y.Z -m "<short summary of changes since previous tag>"
```

## 6. Push

Pushing the tag triggers `.github/workflows/python-publish.yml`, which builds an sdist/wheel and publishes to PyPI.

```bash
git push origin master
git push origin vX.Y.Z
```

## Notes

- Never bump `version` anywhere else; `setup.py` is the single source of truth.
- Never force-push tags or rewrite existing release commits.
- If the user only asks to prepare the release, stop after step 5 and let them push.
