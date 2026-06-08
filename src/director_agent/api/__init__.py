"""FastAPI surface for the production pipeline agent.

The app object lives in `app.py` and is referenced directly (see the
`[tool.vercel] entrypoint` in pyproject.toml). This package intentionally does
NOT re-export `app` — doing so made two import paths look like FastAPI
entrypoints and broke Vercel's auto-detection.
"""
