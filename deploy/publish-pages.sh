#!/usr/bin/env bash
# Publishes the trainer assistant to GitHub Pages.
#
# GitHub Pages can serve the site from the gh-pages branch, so the whole
# publication is: build the page with the password gate switched on, then push
# it to that branch. The branch is what Pages actually serves.
#
#   deploy/publish-pages.sh              # password from GATE_PASSWORD
#   deploy/publish-pages.sh 3321         # password as an argument
#
# Pages must already be enabled for the repository:
#   Settings -> Pages -> Deploy from a branch -> gh-pages / (root)
#
# The alternative is the workflow .github/workflows/pages.yml, which publishes
# automatically on every push to main. A GitHub token can only push that file
# with the `workflow` scope (gh auth refresh -h github.com -s workflow), so
# this script is the path that works with an ordinary token.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
REPO="https://github.com/glebvzahar-maker/rzd-trainer-assistant.git"
BRANCH="gh-pages"
PASSWORD="${1:-${GATE_PASSWORD:-}}"

if [ -z "$PASSWORD" ]; then
  echo "Пароль не задан: передайте его аргументом или задайте GATE_PASSWORD." >&2
  exit 1
fi

echo "→ собираю страницу с входом по паролю"
node "$HERE/build-pages.mjs" --password "$PASSWORD" --out "$ROOT/docs"

echo "→ публикую ветку $BRANCH"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp "$ROOT/docs/index.html" "$WORK/index.html"
(
  cd "$WORK"
  git init -q -b "$BRANCH"
  git add index.html
  git -c user.name="Глеб Захаренко" -c user.email="gleb.v.zahar@gmail.com" \
      commit -q -m "Сборка страницы для GitHub Pages"
  git push -f "$REPO" "$BRANCH"
)

echo "→ готово: https://glebvzahar-maker.github.io/rzd-trainer-assistant/"
echo "  сборка Pages занимает около минуты"
