#!/bin/sh
DATE=`date "+%Y%m%d%H%M"`
COMMIT=`git rev-parse HEAD`
SHORTCOMMIT=`git rev-parse --short=8 HEAD`

cp locutus.spec.tmpl locutus.spec

sed -i -e "s;@@DATE@@;${DATE};" locutus.spec
sed -i -e "s;@@COMMIT@@;${COMMIT};" locutus.spec
sed -i -e "s;@@SHORTCOMMIT@@;${SHORTCOMMIT};" locutus.spec
