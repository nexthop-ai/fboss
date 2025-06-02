#!/usr/bin/env python3

# Enter the FBOSS build container with everything mounted

import os.path
import importlib
import subprocess
docker_build = importlib.import_module("docker-build")

proc = subprocess.run(["docker", "ps", "-a"], capture_output=True)
if proc.returncode == 0 and "FBOSS_BUILD_CONTAINER" not in proc.stdout.decode():
    branch_name = subprocess.run("git status | awk '/On branch/ {print $3}'", shell=True,
                                 capture_output=True).stdout.decode().strip()
    docker_build.run_fboss_build(scratch_path=os.path.expandvars("$HOME/work/fboss_build-" +
                                                                 branch_name), target=None,
                                 docker_output=True, use_system_deps=True, env_vars=[],
                                 use_local=True, num_jobs=None, schedule_type=None,
                                 cache_config=None, extras_dir=os.path.abspath("../"), build=False)
else:
    proc = subprocess.run(["docker", "ps"], capture_output=True)
    if proc.returncode == 0 and "FBOSS_BUILD_CONTAINER" not in proc.stdout.decode():
        subprocess.run(["docker", "start", "FBOSS_BUILD_CONTAINER"])

    subprocess.run(["docker", "exec", "-it", "FBOSS_BUILD_CONTAINER", "bash"])
