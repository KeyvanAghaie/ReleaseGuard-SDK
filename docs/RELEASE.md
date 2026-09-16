# Publication checklist

Current status: local implementation; no GitHub repository, tag, or Vercel URL
has been published from this workspace yet. Do not advertise a live deployment
until its URL has been checked.

## Before publication

- [ ] Python tests and Ruff pass.
- [ ] React typecheck and production build pass.
- [ ] SDK wheel and source distribution build.
- [ ] Built wheel installs and imports independently.
- [ ] Example and real local overhead benchmark run.
- [ ] Browser checks cover success, injected failure, concurrent roots and export.
- [ ] GitHub owner and repository visibility are confirmed.
- [ ] Vercel is connected to the standalone repository.

## GitHub

Create an empty public repository named releaseguard-sdk. Push the contents of
this folder as its root, excluding .venv, node_modules and ignored build outputs.
Do not push the parent roadmap or other project folders.

Run CI on main before tagging. A v0.1.0 tag triggers the release workflow, which
checks the version, reruns validation, builds distributions and uploads them
with the benchmark. PyPI is not required for this release.

## Vercel

Import the standalone GitHub repository. Select the FastAPI framework preset,
with repository root as the Root Directory. The Python entrypoint is app:app
in pyproject.toml. vercel.json builds the React frontend with pnpm.

Keep the framework's output directory defaults; do not change it to dist.
The SDK Python package uses dist for release archives, while the UI builds to
frontend-dist. requirements.txt installs the local package with demo extras.
No model API key or database environment variables are needed.

After deployment, verify /api/health, /docs and all three scenarios at the
public URL. Ensure deployment protection allows the intended public demo.
A local build alone does not prove the Vercel deployment passed.

Then add the verified URL to the GitHub About field and README. If a release
fails verification, do not silently move an existing tag: fix and publish a
new patch version.

