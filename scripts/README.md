# Profile cards

`generate_profile_cards.py` uses Python's standard library and GitHub's public REST API. The daily `Update profile cards` workflow regenerates and commits both SVGs to `assets/stats/`; it can also be run manually from Actions. The README uses these committed files, so a failed API call leaves the last successful cards visible.

No external stats server, Python packages, or personal access token is required. Actions uses the repository-scoped `github.token`. Only the generation job needs contents write permission to commit the cards.

The stats card shows stars and forks received by owned public non-fork repositories, the number of those repositories, and public pull requests and issues authored by the profile owner. Language percentages use code bytes across owned public non-fork repositories (including archived repositories); the six largest are displayed, with percentages normalized across those six. These measure repository contents, not proficiency or time spent coding. Private repositories are excluded.

Run locally from the repository root:

```sh
python3 scripts/generate_profile_cards.py --username GoblinRules
```

Set `GH_TOKEN` to an existing GitHub token if you need higher API rate limits locally. Never commit a token. API failures stop the run before the existing cards are replaced.

The typing banner, tech badges, and streak card in the README still use their existing external services. The contribution snake has its own workflow and output branch.
