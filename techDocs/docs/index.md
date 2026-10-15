# brunosouzas

The GitHub profile page of Bruno Souza (github.com/brunosouzas), branded with the artwork of [brunosouzas.com](https://brunosouzas.com/).

## How it is built

- `README.md` is the page. Its latest-articles block is generated from the site's RSS feed by `scripts/update_articles.py`, daily, by the `Latest articles` workflow.
- `assets/site/` holds copies of the site's artwork; `scripts/build_assets.py` composes them into the header, the category cards and the link buttons in `assets/`.
- `python3 -m unittest discover -s tests` runs the tests; the `Checks` workflow runs them and checks that `assets/` matches the script's output.

## When the site artwork changes

1. Copy the changed files from `public/images/home/` of the brunosouzas.com repository into `assets/site/`.
2. Run `python3 scripts/build_assets.py` and commit `assets/`.
