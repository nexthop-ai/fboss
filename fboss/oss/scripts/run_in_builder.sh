#!/bin/bash
# Run a script inside the build container
#
# $CWD will be bind-mounted to /var/FBOSS/fboss in the container

interactive=""
if [ "$1" = "bash" ]; then
  interactive="-it"
fi

docker run $interactive --rm --volume $PWD:/var/FBOSS/fboss --volume $HOME/.config/gh:/root/.config/gh \
  --env BASH_ENV=/root/.bashrc fboss_builder /bin/bash -c "$@"
