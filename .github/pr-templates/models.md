<!-- tt-awesome-digest-boilerplate -->
Nightly rebuild of `src/_data/models.json` from tt-inference-server (main branch) and tt-model
(`scripts/build_models_data.py`). When the run changed something, the list above this line says what
(`scripts/models_diff.py`); on Thursdays the same run adds the week's models roundup to
`src/_data/planet_feeds.json`.

Status, context and users are copied from the release spec. Nothing is measured.
A model that exists only as a tt-model bundle takes its kind from the task tag on its card. A bundle
with no tag takes its kind from `scripts/data/model_kinds_inferred.json` when that file has an entry
for its weights repo, and the page says the kind was inferred. A bundle with neither is listed as
"task not stated" and needs an entry in that file.
