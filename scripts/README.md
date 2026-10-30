# scripts

Helper scripts. Run them from the repository root.

| Script | What it does | Needs |
| --- | --- | --- |
| `try_all_cases.py` | Tries all 25 approval cases against a fresh server (or `--url`) and prints PASS or FAIL for each; exit code 0 only if all pass | Python |
| `run_mutation.sh <label>` | Mutation tests the domain package with mutmut and writes `docs/mutation/<label>.txt` | WSL or Linux (mutmut needs `fork()`) |
| `show_survivors.sh` | Prints the diff of every surviving mutant from the last run | WSL or Linux |
| `build_docs.py` | Builds the documentation PDFs into `docs/pdf/`; `--kit` builds the personal kits; `--combined` builds one merged PDF | `pip install -e "backend[docs]"` |
| `summarize_log.py` | Validates the AI interaction log (same 27 keys, unique ids, links resolve) and writes `logs/ai-interactions-summary.md` | Python |
| `generate_code_reference.py` | Writes `docs/guides/20-code-reference.md` from the docstrings and comments in the code | Python |
| `make_demo_video.py` | Records the demo video (every command runs live while recorded) into `docs/video/` | `imageio-ffmpeg`, Playwright, Windows speech |

## Examples

```text
python scripts/try_all_cases.py
wsl -d Ubuntu-22.04 -- bash scripts/run_mutation.sh after
python scripts/generate_code_reference.py && python scripts/build_docs.py
```
