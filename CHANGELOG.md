# Changelog

All notable changes to the **Self-Healing Playwright Engine (Lite)** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
**Author / Maintainer:** Roza212 (`186386856+Roza212@users.noreply.github.com`)

---

## [Unreleased]

### Added — Phase 0: Project Scaffolding & Documentation
- **Project Rules & Specification**:
  - Added `.agents/rules/project-rules.md` defining strict engineering constraints (Python 3.11, Playwright Sync API, no `time.sleep`, strict Page Object `ElementSpec` separation, read-only healer, no `data-truth` leakage).
  - Added `docs/SPEC.md` specifying the 3-tier self-healing architecture (T1 primary selector, T2 ARIA role fallback, T3 MiniLM + role + spatial + attribute Jaccard scoring), hard gates, SSIM visual verification, and benchmark mutation requirements.
- **Scaffolding & Configuration**:
  - Added `requirements.txt` pinning Playwright, pytest, pytest-playwright, pytest-html, sentence-transformers, scikit-learn, numpy, opencv-python-headless, scikit-image, and ruff.
  - Added `pytest.ini` configuring test discovery (`tests`), self-contained HTML reports (`reports/report.html`), and strict markers (`unit`, `heal`, `visual`, `live`).
  - Added `pyproject.toml` configuring Ruff (`line-length = 100`, `py311`, lint rules `E, F, I, B, TID`, and banned API enforcement against `time.sleep`).
  - Added `.gitignore` excluding `.venv/`, `reports/`, `__pycache__/`, `.pytest_cache/`, and `.env`.
  - Initialized Python package directories with `__init__.py` in `core/`, `pages/`, `mockbench/`, `tests/`, and `benchmarks/`.
- **Documentation**:
  - Added `COMMANDS_USED.md` documenting all CLI commands used in setting up and verifying the project.
  - Added `FILE_GUIDE.md` explaining the purpose and key directives/functions of every file created so far.
