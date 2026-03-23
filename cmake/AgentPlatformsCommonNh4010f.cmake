# CMake to build libraries and binaries in fboss/agent/platforms/common/nh4010f

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(nh4010f_platform_mapping
  fboss/agent/platforms/common/nh4010f/Nh4010fPlatformMapping.cpp
)

target_link_libraries(nh4010f_platform_mapping
  platform_mapping
)
