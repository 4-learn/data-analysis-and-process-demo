#!/usr/bin/env bash
# 教師用：在隔離的 docker 網路裡起 MariaDB 11.8，實跑第 04 節第六段的所有宣稱（pandas 3.0.6 與 2.3.3 各一次）。
# 用法：bash tools/mariadb-04/run.sh > tools/mariadb-04/evidence.txt
# 需要 docker；不連教室資料庫、不需要本機安裝 libmariadb-dev。結束後移除容器與網路。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="$(cd "$HERE/../../data" && pwd)"
WORK="$(mktemp -d)"
trap 'docker rm -f da-mdb >/dev/null 2>&1 || true; docker network rm da-mdb-net >/dev/null 2>&1 || true; rm -rf "$WORK"' EXIT
cp "$HERE/probe.py" "$HERE/probe2.py" "$DATA/articles.jsonl" "$HERE/../../04-sql-or-pandas.md" "$WORK/"
docker network create da-mdb-net >/dev/null
docker run -d --rm --name da-mdb --network da-mdb-net -e MARIADB_ROOT_PASSWORD=pw -e MARIADB_DATABASE=crawler_course mariadb:11.8 >/dev/null
for i in $(seq 60); do docker exec da-mdb mariadb -uroot -ppw -e 'SELECT 1' >/dev/null 2>&1 && break; sleep 1; done
for P in 3.0.6 2.3.3; do
  echo "## pandas $P"
  docker run --rm --network da-mdb-net -v "$WORK":/w -w /w -e PANDAS=$P python:3.11-slim bash -c \
    'apt-get update -qq >/dev/null 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libmariadb-dev gcc >/dev/null 2>&1; pip install -q mariadb==1.1.14 pandas==$PANDAS >/dev/null 2>&1; python -W ignore probe.py; python probe2.py' 2>/dev/null
done
