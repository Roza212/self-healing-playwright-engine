New-Item -ItemType Directory -Force core,pages,mockbench,tests,benchmarks,docs,.agents/rules,.github/workflows

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu

.agents/rules/project-rules.md → paste rules block from guide.
docs/SPEC.md → paste spec block from guide.
