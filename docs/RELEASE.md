# Publication checklist

Current status: source is present on the public GitHub repository's main branch.
The v0.1.0 tag and GitHub Release have not yet been created. No verified Vercel
URL is available. Do not advertise a live deployment until its URL is checked.

## Before publication

- [x] Python tests (28) and Ruff pass locally.
- [x] React typecheck and production build pass locally.
- [x] SDK wheel and source distribution build locally.
- [x] Built wheel imports independently from its archive, outside source paths.
- [x] Example and real local overhead benchmark run.
- [x] Browser checks cover success, injected failure, concurrent roots and export.
- [x] GitHub repository and main branch are reachable; visibility requires public page check.
- [ ] CI passes on the final pushed commit.
- [ ] v0.1.0 GitHub Release contains wheel, sdist and benchmark.
- [ ] Vercel is connected to the standalone repository.
- [ ] Public Vercel deployment passes browser and API smoke checks.

## GitHub

The repository already exists at https://github.com/KeyvanAghaie/releaseguard-sdk.
Push the contents of this folder as its root, excluding .venv, node_modules and
ignored build outputs. Do not push the parent roadmap or other project folders.

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
