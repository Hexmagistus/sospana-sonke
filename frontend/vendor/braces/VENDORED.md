# Vendored braces 3.0.4

This is the published `braces@3.0.3` source (MIT, Jon Schlinkert) plus a nesting-depth limit.

npm still has no release newer than 3.0.3. GitHub advisory GHSA-vfj7-8cjw-p6xm (CVE-2026-93687) covers `<= 3.0.3` and lists no patched version. `npm update braces` cannot leave that range, and `npm audit fix --force` would install Tailwind 4.

The depth limit follows the unmerged change in micromatch/braces#72 (`d0d575e55e74a4e0218e5248fafb79efc3e54ebb`): brace and parenthesis nesting stops at 100, and `compile`, `expand`, and `stringify` refuse an AST deeper than that. Two local adjustments:

- `maxDepth` is floored to an integer, so a fractional limit cannot admit an extra nesting level.
- `stringify` still walks with an empty parent, as 3.0.3 does. Passing the current node (as that pull request does) changes `escapeInvalid` output for ordinary patterns.

The package version is `3.0.4` so it sits outside the advisory range. It is not a release from the `braces` maintainers. Replace this directory with the real release when one is published, and drop the `braces` override.
