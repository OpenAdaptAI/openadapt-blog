# Voice lint fixtures

Written for the tests in `tests/test_voice_lint.py`. None of this text is
copied from anywhere.

- `plain_*.md` are ordinary prose in the style the blog asks for. The lint
  must pass them with no FAIL, in default and `--strict` mode, and with none
  of the per-hit pattern warnings (signposting, negative parallels, fragment
  runs, colon reveals, "-ing" tails, vocabulary, stock phrases).
- `slop_*.md` each carry one family of patterns. The tests check that the
  matching rule fires and that the others stay quiet where they should.

The tests skip this README: it isn't a fixture.
