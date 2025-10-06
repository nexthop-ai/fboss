#!/bin/bash
if ! $(docker images | grep -q fboss_builder); then
    cat fboss/fboss_builder.tar | docker image load
fi

cp fboss/$1 $1
./fboss/fboss/oss/scripts/run_in_builder.sh ./$1
rm $1
