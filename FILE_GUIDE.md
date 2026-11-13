# Project File Guide (`self-healing-lite`)

**Author:** Roza212 (`186386856+Roza212@users.noreply.github.com`)  
**Repository:** https://github.com/Roza212/self-healing-playwright-engine.git

This document explains every file created in the project up to **Phase 0 (Project Scaffolding)**, what role each file plays in the architecture, and what key settings, rules, or functions/directives live inside each one.

---

## 1. Architecture & Rules Documentation

### `.agents/rules/project-rules.md`
- **What it does:** Defines the non-negotiable engineering and testing constraints for the Self-Healing Playwright Engine (Lite) that both developers and AI agents must obey.
- **Important Rules & Directives inside:**
  - **Tech stack lock:** Python 3.11, Playwright **Sync API**, `pytest`, and 100% free/local tools (no paid external APIs).
  - **No hard sleeps:** Bans `time.sleep()` and `page.wait_for_timeout()`. Enforces Playwright auto-waiting, `locator.wait_for()`, and `expect()`.
  - **Strict Page Object Model (POM):** Tests in `tests/` must never contain raw CSS/XPath selectors; every locator is declared as an `ElementSpec` inside `pages/`.
  - **Read-only healer & anti-cheating rule:** The healer never mutates the DOM under test, and the DOM extractor is strictly forbidden from reading or exporting the ground-truth `data-truth` attribute used by the benchmark harness.
  - **Config immutability:** Prohibits changing scoring weights or thresholds in `core/config.py` unless explicitly requested.

---

### `docs/SPEC.md`
- **What it does:** Serves as the functional specification for the 3-tier self-healing locator engine, visual regression guard, and mutation benchmark.
- **Important Logic & Specifications defined inside:**
  - **Tier 1 (T1 - Primary Selector):** Waits for the primary selector to become visible. If it succeeds, captures and caches the element's baseline DOM/spatial fingerprint (if not already stored).
  - **Tier 2 (T2 - ARIA Role Fallback):** Uses Playwright's native `get_by_role(role, name=accessible_name, exact=True)`. Requires exactly 1 visible match that passes all hard gates.
  - **Tier 3 (T3 - Multi-Signal Semantic Healer):** Scores all visible DOM candidates using:
    - **MiniLM Cosine Similarity** (`0.55` weight) via `sentence-transformers/all-MiniLM-L6-v2`
    - **Spatial Proximity** (`0.20` weight)
    - **ARIA/HTML Role Match** (`0.15` weight)
    - **Attribute Jaccard Similarity** (`0.10` weight)
    - Weights are dynamically re-normalized over whichever signals are present.
  - **Hard Gates (Immediate Disqualifiers):** Rejects candidates that are `hidden`, `disabled`, have a `role_mismatch`, trigger an `opposite_action` (e.g., cancel/delete vs. submit), or `moved_far` (`spatial < 0.10`).
  - **Acceptance Thresholds & Refusal:** Requires score `>= 0.70` (`>= 0.85` for high-risk actions) and a minimum margin of `>= 0.08` between the #1 and #2 candidates. Otherwise raises `HealingRefused(AssertionError)` listing the top-3 candidates.
  - **Post-Heal Visual Guard:** Runs Structural Similarity Index (**SSIM**) against the pre-drift screenshot plus an occlusion check after any heal.
  - **Benchmark Contract:** Must successfully heal 6 drift mutations to `data-truth="submit"`, and must refuse `element_removed` and `decoy_far`.

---

## 2. Configuration & Tooling Files (Phase 0)

### `requirements.txt`
- **What it does:** Declares all third-party Python packages required by the engine, test runner, ML scorer, and visual guard (excluding CPU PyTorch, which is installed first from the PyTorch CPU wheel index).
- **Important Packages & Functions Provided:**
  - `playwright>=1.49`: Browser automation and sync DOM interaction API.
  - `pytest>=8.0`, `pytest-playwright>=0.5`, `pytest-html>=4.1`: Test execution framework, Playwright browser fixtures (`page`, `context`), and self-contained HTML report generation (`reports/report.html`).
  - `sentence-transformers>=3.0`: Loads `all-MiniLM-L6-v2` to compute semantic text embeddings (`model.encode()`).
  - `scikit-learn>=1.5` & `numpy>=1.26`: Vector math and cosine similarity calculation for Tier 3 candidate ranking.
  - `opencv-python-headless>=4.9` & `scikit-image>=0.22`: Image decoding (`cv2`) and Structural Similarity (`skimage.metrics.structural_similarity`) for post-heal visual verification.
  - `ruff>=0.6`: Fast Rust-based Python linter and import sorter.

---

### `pytest.ini`
- **What it does:** Configures `pytest` discovery, command-line defaults, HTML reporting, and strict custom test markers.
- **Important Directives inside:**
  - `testpaths = tests`: Restricts test collection to the `tests/` folder.
  - `addopts = -ra --strict-markers --html=reports/report.html --self-contained-html`:
    - `-ra`: Shows a short test summary for all non-passing tests (skipped, failed, xfailed).
    - `--strict-markers`: Fails immediately if a test uses an unregistered `@pytest.mark.<name>` typo.
    - `--html=reports/report.html --self-contained-html`: Automatically writes a single portable HTML test report on every run.
  - `markers`: Registers the 4 test tiers so you can run subsets selectively (e.g., `pytest -m unit`):
    - `unit`: Fast pure-Python unit tests (no browser required).
    - `heal`: DOM mutation benchmark healing tests.
    - `visual`: SSIM visual comparison and occlusion tests.
    - `live`: Tests running against a live public site.

---

### `pyproject.toml`
- **What it does:** Configures **Ruff** for code quality, formatting width, import sorting, and static enforcement of project rules.
- **Important Sections & Rules inside:**
  - `[tool.ruff]`: Sets `line-length = 100` and `target-version = "py311"`.
  - `[tool.ruff.lint]`: Enables rule families:
    - `E`, `F`: Pycodestyle errors and Pyflakes (undefined names, unused variables/imports).
    - `I`: `isort` import sorting.
    - `B`: `flake8-bugbear` (catches common Python bug patterns).
    - `TID`: `flake8-tidy-imports` (enforces banned API rules).
  - `[tool.ruff.lint.flake8-tidy-imports.banned-api]`: Statically bans `"time.sleep"` across the entire codebase with the error message: `"Use Playwright auto-wait or expect()"`. If anyone writes `from time import sleep` or `time.sleep(...)`, `ruff check .` fails immediately.

---

### `.gitignore`
- **What it does:** Prevents local virtual environments, generated HTML reports, Python bytecode caches, and secret files from being committed to Git.
- **Ignored Paths:**
  - `.venv/` (local Python 3.11 virtual environment)
  - `reports/` (generated `report.html` test outputs)
  - `__pycache__/` and `.pytest_cache/` (interpreter and test runner caches)
  - `.env` (local environment variables)

---

## 3. Package Initializers (`__init__.py`)

Empty `__init__.py` files turn each directory into an importable Python package so modules can cleanly import one another (e.g., `from core.config import ...`):

| File | Purpose in Upcoming Phases |
| :--- | :--- |
| `core/__init__.py` | Marks `core/` as the package that will house the healing engine (`config.py`, `types.py`, `extractor.py`, `scorer.py`, `healer.py`, `visual.py`). |
| `pages/__init__.py` | Marks `pages/` as the Page Object Model package where `ElementSpec` definitions and page classes live. |
| `mockbench/__init__.py` | Marks `mockbench/` as the package for the local deterministic HTML app and DOM drift mutation injectors. |
| `tests/__init__.py` | Marks `tests/` as the test suite package for unit, healing, visual, and live Playwright tests. |
| `benchmarks/__init__.py` | Marks `benchmarks/` as the package for benchmark runners and metrics aggregation. |

---

## 4. Reference & Project Logs

### `COMMANDS_USED.md`
- **What it does:** Documents every PowerShell, Python, `.venv`, Git, and verification command run in the workspace, grouped by category with explanations.

### `CHANGELOG.md`
- **What it does:** Tracks notable additions, changes, and phase completions across the project following the *Keep a Changelog* format.
