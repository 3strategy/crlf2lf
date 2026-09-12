---
name: crlf2lf
description: Normalize CRLF or mixed text-file line endings to LF across a project. Use when a user requests CRLF-to-LF conversion, Unix/macOS line endings, or a check for non-LF files; do not rewrite binary or generated dependency files.
---

# CRLF to LF

Convert the requested project in one pass:

```text
python <skill-directory>/scripts/crlf2lf.py <project-root> --git-tracked --write
```

Use `--git-tracked` for tracked working-tree files, including metadata such as `.idea`. Omit it outside Git or when the requested scope includes untracked files; directory traversal skips common generated and dependency folders. A single file path is also supported without `--git-tracked`.

The helper converts CRLF and stray CR to LF, preserves other bytes, and skips symlinks and likely binaries. Report its conversion count and any errors. Routine conversion needs no separate preview, rescan, or project build. For a requested audit use `--check` instead of `--write` (exit 1 means conversion needed); omit both for a preview.
