# docs

Documentation for the invoice approval app.

## Guides (Markdown sources in `guides/`, PDFs in `pdf/`)

| # | Guide | Read it to |
| --- | --- | --- |
| 01 | Project Overview | see what was built and where it stands |
| 02 | Requirements Specification | know the rules, decisions and test traceability |
| 03 | Architecture and Design | understand layers, data model and decisions |
| 04 | API Reference | call the service |
| 05 | User Guide | use the web UI |
| 06 | Developer Guide | set up, run and extend |
| 07 | Test Plan and Report | see what is tested and why |
| 08 | Mutation Testing Report | see the before and after scores |
| 09 | Code Review Report | see every review finding and verdict (`pr-review.md`) |
| 10 | AI Workflow Guide | see agents, skills, hooks and the log |
| 11 | Operations and Security | know limits and follow-ups |
| 12 | Specification Pack | read the Spec Kit artifacts |
| 13 | Assignment Report | see how each assignment item was met |
| 14 | Appendix | agent conventions and feature briefs |
| 15 | Demo Video Script | record the demo |
| 16 | Submission Checklist | see what is done and open |
| 17 | Recording Runbook | follow a step-by-step recording guide |
| 18 | Run and Test Guide | run the project and test every case |
| 19 | SOLID Design | see how each principle is followed |
| 20 | Code Reference | look up every module, class and function (generated from the docstrings) |
| 21 | Architecture Diagrams | see the system, one request, the rules, the lifecycle, the AI workflow and the test layers |
| 22 | Reviewer Guide | judge the work: what to open and how to check every claim |
| 23 | UI Walkthrough | see every screen of the app, with real screenshots |

## Other folders

| Folder | Contents |
| --- | --- |
| `mutation/` | Mutation reports: `baseline.txt` (before), `after-first-pass.txt`, `after.txt`, `after-solid-refactor.txt` |
| `pdf/` | The guides as PDFs, one file each |
| `presentations/` | Two slide decks, each as PowerPoint and PDF: the reviewer walkthrough (the whole project) and the UI walkthrough (screen by screen) |
| `use-cases/` | Short briefs for features we may build |
| `video/` | The demo video (git-ignored) |

## Rebuild the PDFs

```text
pip install -e "backend[docs]"
python scripts/generate_code_reference.py
python scripts/make_diagrams.py     # architecture diagrams (docs/guides/img/diagrams)
python scripts/ui_screens.py        # crop the raw screenshots in UI/ (docs/guides/img/ui)
python scripts/build_docs.py
python scripts/make_decks.py        # slide decks (docs/presentations)
```

## Documentation in the code itself

- Every Python module, class and function has a docstring: what it is for, and for non-obvious ones its arguments, return value and errors.
- Comments explain **why**, not what: for example why a lock is needed, why a list is copied, why an amount is safe as a float.
- The web UI (`app.js`, `styles.css`, `index.html`), the end-to-end tests and the configuration files are commented the same way.
