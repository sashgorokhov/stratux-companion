set -ex

cd $DEPLOYMENT_DIR

# Pull new updates...
git fetch --all
# Reset local files
git reset --hard origin/master

source $DEPLOYMENT_DIR/env/bin/activate
$DEPLOYMENT_DIR/env/bin/poetry install
