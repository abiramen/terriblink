#!/bin/bash
app="terriblink"
docker build -t ${app} .
docker run -d -p 1093:80 --env-file ./.env --name=${app} -v $PWD:/app ${app}
