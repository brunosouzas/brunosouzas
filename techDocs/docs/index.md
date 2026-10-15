# brunosouzas

The GitHub profile page of Bruno Souza (github.com/brunosouzas), branded with the artwork of [brunosouzas.com](https://brunosouzas.com/).

## How it is built

- `README.md` is the page: the header, the latest articles and the "Find me" buttons.
- The latest articles are cards in `assets/articles/`, drawn by `scripts/update_articles.py` from the site's RSS feed (title, date and the cover in `media:content`), daily, by the `Latest articles` workflow.
- `assets/site/` holds copies of the site's artwork; `scripts/build_assets.py` composes them into the header and the buttons in `assets/`.
- `python3 -m unittest discover -s tests` runs the tests; the `Checks` workflow runs them and checks that `assets/` matches the script's output.

## When the site artwork changes

1. Copy the changed files from `public/images/home/` of the brunosouzas.com repository into `assets/site/`.
2. Run `python3 scripts/build_assets.py` and commit `assets/`.
