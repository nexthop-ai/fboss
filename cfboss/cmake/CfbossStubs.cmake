# CMake to build the cFBOSS service-stub binaries.
#
# When BUILD_CFBOSS is ON, this file defines qsfp_service, platform_manager,
# sensor_service, fan_service, data_corral_service, and led_service as copies
# of a single stub binary. The corresponding per-service .cmake files
# (QsfpService.cmake, PlatformPlatformManager.cmake, etc.) gate their real
# binary definitions on `if(NOT BUILD_CFBOSS)` so that exactly one definition
# per target exists in any single CMake configure.

if(NOT BUILD_CFBOSS)
  return()
endif()

set(_CFBOSS_STUB_SRC cfboss/src/CfbossServiceStub.cpp)
set(_CFBOSS_STUB_TARGETS
  qsfp_service
  platform_manager
  sensor_service
  fan_service
  data_corral_service
  led_service
)

foreach(target IN LISTS _CFBOSS_STUB_TARGETS)
  add_executable(${target} ${_CFBOSS_STUB_SRC})
  target_link_libraries(${target}
    ${SYSTEMD}
    gflags_shared
  )
  install(TARGETS ${target})
endforeach()
