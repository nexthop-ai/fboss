# CMake to build libraries and binaries in fboss/agent/platforms/common/nh4220f

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(nh4220f_platform_mapping
  fboss/agent/platforms/common/nh4220f/Nh4220fPlatformMapping.cpp
)

target_link_libraries(nh4220f_platform_mapping
  platform_mapping
)
