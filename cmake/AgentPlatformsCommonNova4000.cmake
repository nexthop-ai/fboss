# CMake to build libraries and binaries in fboss/agent/platforms/common/nova4000

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(nova4000_platform_mapping
  fboss/agent/platforms/common/nova4000/Nova4000PlatformMapping.cpp
)

target_link_libraries(nova4000_platform_mapping
  platform_mapping
)
