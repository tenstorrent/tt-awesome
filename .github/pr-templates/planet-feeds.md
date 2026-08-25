Automated planet feed refresh.

New items from Reddit and untrusted community feeds start as `approved: false`.
Flip any you want to publish to `true`, then merge. Items already `approved: true`
(YouTube, arXiv) are safe to merge without review.

Stored approval flags are preserved across runs, so an item left `approved: false`
stays unpublished and won't reappear in a later diff. For posts you've decided
against for good, record the decision instead of leaving them pending:

```
python3 scripts/decline_planet_item.py <url> [<url> …] --reason off-topic
```

That moves them to `src/_data/planet_declined.json`, and the fetcher treats those
URLs as known so the source never re-proposes them.
