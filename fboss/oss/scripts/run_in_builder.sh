#!/bin/bash
# Run a script inside the build container
#
# $CWD will be bind-mounted to /var/FBOSS/fboss in the container

docker run -it --rm --volume $PWD:/var/src --volume $HOME/.config/gh:/root/.config/gh \
    --env BASH_ENV=/root/.bashrc fboss_builder /bin/bash -c $@
