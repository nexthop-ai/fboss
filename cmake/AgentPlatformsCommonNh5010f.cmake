# CMake to build libraries and binaries in fboss/agent/platforms/common/nh5010f

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(nh5010f_platform_mapping
  fboss/agent/platforms/common/nh5010f/Nh5010fPlatformMapping.cpp
)

target_link_libraries(nh5010f_platform_mapping
  platform_mapping
)
