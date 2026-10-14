# OpenAdapt Blog

> **Lifecycle: Internal.** This repository is the publishing source for the
> public [OpenAdapt Blog](https://blog.openadapt.ai/). It is not an OpenAdapt
> product package or runtime.

The site uses Hugo and publishes from `main` through GitHub Pages. Posts are in
`content/posts/`. The public site contains guides, product updates, and bounded
evaluation reports from the OpenAdapt project.

For a local preview:

```bash
git submodule update --init --recursive
hugo server
```

Use the canonical product documentation at
[docs.openadapt.ai](https://docs.openadapt.ai/) for installation and operating
instructions.

## Writing or editing a post

Public text follows two references: the Microsoft Writing Style Guide for how
to write, and Wikipedia's "Signs of AI writing" for what to check a draft
against. [docs/AUTOMATION.md](docs/AUTOMATION.md#voice) explains how the lints
use them. Before you open a pull request:

```bash
python3 scripts/lint_post_voice.py --strict content/posts/<slug>/index.md
python3 scripts/lint_post_substance.py --strict content/posts/<slug>/index.md
python3 scripts/check_benchmark_claims.py
python3 -m unittest discover -s tests
hugo --minify
```

Every post ends with the same call to action from
`layouts/partials/post_cta.html`, so don't write one into the post.
