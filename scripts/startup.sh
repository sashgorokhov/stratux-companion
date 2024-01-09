set -ex

cd $DEPLOYMENT_DIR
git pull $SOURCE_REPO

$DEPLOYMENT_DIR/env/bin/poetry install
