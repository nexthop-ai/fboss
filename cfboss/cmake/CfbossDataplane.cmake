# CMake for the cfboss dataplane library. This file is included from
# CMakeLists.txt; everything below is gated on BUILD_CFBOSS so distro
# builds never compile or link any of it.
#
# The static initializer in CfbossDataplaneRegistration.cpp is the entire
# point of this library — it is the trigger that wires the cfboss-side
# behavior into FBOSS's generic InitHookRegistry
# points. The library MUST be linked with --whole-archive (below) so the
# initializer's translation unit is not discarded for lack of external
# references.

if(NOT BUILD_CFBOSS)
  return()
endif()

add_library(cfboss_dataplane
  cfboss/dataplane/CfbossDataplaneRegistration.cpp
  cfboss/dataplane/KernelRouteSyncer.cpp
  cfboss/dataplane/NetlinkUtils.cpp
  cfboss/dataplane/PortMap.cpp
  cfboss/dataplane/VethIpInstaller.cpp
  cfboss/dataplane/VethPacketBackend.cpp
)

target_link_libraries(cfboss_dataplane
  core
  fake_sai
  init_hook_registry
  ${NETLINKROUTE3}
  ${LIBNL}
  ${RE2}
)

# Link into both agent binaries with --whole-archive so the static-init
# constructor in CfbossDataplaneRegistration.cpp actually runs.
target_link_libraries(fboss_sw_agent
  -Wl,--whole-archive
  cfboss_dataplane
  -Wl,--no-whole-archive
)

target_link_libraries(fboss_hw_agent-sai_impl
  -Wl,--whole-archive
  cfboss_dataplane
  -Wl,--no-whole-archive
)

# PortMap parser/validator unit test (gtest).
add_executable(cfboss_port_map_test
  cfboss/dataplane/test/PortMapTest.cpp
)

target_link_libraries(cfboss_port_map_test
  cfboss_dataplane
  ${GTEST}
  ${LIBGMOCK_LIBRARIES}
)

# Point the shipped-config parse test at the in-tree port_map.json.
target_compile_definitions(cfboss_port_map_test PRIVATE
  CFBOSS_PORT_MAP_JSON="${CMAKE_CURRENT_SOURCE_DIR}/fboss-image/image_builder/templates/centos-09.0/root_files_cfboss/etc/fboss/cfboss/port_map.json"
)

gtest_discover_tests(cfboss_port_map_test)

# VethPacketBackend unit test (gtest) — runs with no privilege or real interfaces.
add_executable(cfboss_veth_packet_backend_test
  cfboss/dataplane/test/VethPacketBackendTest.cpp
)

target_link_libraries(cfboss_veth_packet_backend_test
  cfboss_dataplane
  ${GTEST}
  ${LIBGMOCK_LIBRARIES}
)

gtest_discover_tests(cfboss_veth_packet_backend_test)
