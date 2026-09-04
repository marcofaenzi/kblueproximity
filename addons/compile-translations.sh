#!/bin/sh
# Compile gettext catalogs (source .po -> binary .mo)
set -e
cd "$(dirname "$0")/.."
msgfmt -o LANG/it/LC_MESSAGES/kblueproximity.mo LANG/it/LC_MESSAGES/kblueproximity.po
msgfmt -o LANG/en/LC_MESSAGES/kblueproximity.mo LANG/en/LC_MESSAGES/kblueproximity.po
echo "Compiled Italian and English message catalogs."
