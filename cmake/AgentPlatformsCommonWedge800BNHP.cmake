# CMake to build libraries and binaries in fboss/agent/platforms/common/wedge800bnhp

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(wedge800bnhp_platform_mapping
  fboss/agent/platforms/common/wedge800bnhp/Wedge800BNHPPlatformMapping.cpp
)

target_link_libraries(wedge800bnhp_platform_mapping
  platform_mapping
)
