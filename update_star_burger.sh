#!/bin/bash

set -e

PROJECT_DIR=/opt/star-burger
VENV_PATH=$PROJECT_DIR/venv/bin/activate

cd $PROJECT_DIR

source .env
source $VENV_PATH

git pull
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

npm ci --dev
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"

systemctl restart star-burger.service
systemctl reload nginx.service

commit=`git rev-parse HEAD`

curl -H "X-Rollbar-Access-Token: $ROLLBAR_ACCESS_TOKEN" \
     -H "accept: application/json" \
     -H "content-type: application/json" \
     -X POST "https://api.rollbar.com/api/1/deploy" \
     -d '{
  "environment": "production",
  "revision": "'$commit'",
  "rollbar_username": "admin",
  "local_username": "admin",
  "comment": "deploy",
  "status": "succeeded"
}'


deactivate

if [ $? -eq 0 ]; then
   echo "Деплой успешно завершен."
else
    echo "Деплой не удался."
fi
