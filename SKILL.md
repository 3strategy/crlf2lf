---
name: crlf2lf
description: Normalize CRLF or mixed text-file line endings to LF across a project. Use when a user requests CRLF-to-LF conversion, Unix/macOS line endings, or a check for non-LF files; do not rewrite binary or generated dependency files.
---

# CRLF to LF

Convert the requested project in one pass:

```text
python <skill-directory>/scripts/crlf2lf.py <project-root>
```

By default, the helper applies conversions immediately. For a directory inside a Git worktree it processes tracked files plus untracked files that are not ignored, including tracked metadata such as `.idea`. Outside Git it traverses the directory while skipping common generated and dependency folders. A single file path is also supported.

The helper converts CRLF and stray CR to LF in UTF-8/ASCII text, preserves other bytes, and skips symlinks and likely binaries. Binary checks include known extensions (including PDF and PDF.js `.bcmap`), file signatures, and full-file encoding/control-byte checks. Non-UTF-8 input is conservatively skipped rather than guessing its encoding. Report its conversion count, skipped-file count, and any errors. Routine conversion needs no separate preview, rescan, or project build. For a requested audit use `--check` (exit 1 means conversion needed); use `--preview` to list needed conversions without changing files or returning a failing status. `--git-files` and `--all-files` override automatic scope selection, while `--write` remains available as an explicit form of the default behavior. The legacy `--git-tracked` spelling remains a compatibility alias for `--git-files`.
