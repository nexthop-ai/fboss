# CMake to build libraries and binaries in fboss/agent/platforms/common/nh4010

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(nh4010_platform_mapping
  fboss/agent/platforms/common/nh4010/Nh4010PlatformMapping.cpp
)

target_link_libraries(nh4010_platform_mapping
  platform_mapping
)
