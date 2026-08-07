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
