---
id: building_platform_services
title: Building Platform Services
keywords:
  - FBOSS
  - OSS
  - build
  - docker
oncall: fboss_oss
---

Refer to [Build Page](../build/Building_FBOSS_on_containers.md) for Build
Instructions

Building the entire fboss OSS repository could be time consuming. Optionally,
you can just build the platform services by running

```
<<<<<<< HEAD
time ./build/fbcode_builder/getdeps.py build --allow-system-packages \
--build-type MinSizeRel \
--extra-cmake-defines='{"CMAKE_CXX_STANDARD": "20"}' \
||||||| 81da1b3a3f
time ./build/fbcode_builder/getdeps.py build --allow-system-packages \
--extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20"}' \
=======
time ./fboss/oss/scripts/run-getdeps.py build --allow-system-packages \
--extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20"}' \
>>>>>>> 285e7f8dbe069e649de933f0e791f98560c6c2dd
--scratch-path /var/FBOSS/tmp_bld_dir --cmake-target fboss_platform_services fboss
```

You can also build a specific platform binary by changing the `--cmake_target`.
