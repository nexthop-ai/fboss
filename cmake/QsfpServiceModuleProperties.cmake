# CMake to build libraries and binaries in fboss/qsfp_service/module/properties

# In general, libraries and binaries in fboss/foo/bar are built by
# cmake/FooBar.cmake

add_library(transceiver_properties_manager
    fboss/qsfp_service/module/properties/TransceiverPropertiesManager.cpp
)

target_link_libraries(transceiver_properties_manager
    fboss_error
    switch_config_cpp2
    transceiver_cpp2
    transceiver_properties_cpp2
    Folly::folly
    FBThrift::thriftcpp2
)

add_executable(transceiver_properties_manager_test
    fboss/qsfp_service/module/properties/test/TransceiverPropertiesManagerTest.cpp
    fboss/qsfp_service/module/properties/test/NexthopTransceiverPropertiesDriftTest.cpp
)

# NexthopTransceiverPropertiesDriftTest reads the nexthop.json5 override from
# the source tree and compares it against the compiled-in default table.
target_compile_definitions(transceiver_properties_manager_test PRIVATE
    FBOSS_SOURCE_DIR="${CMAKE_SOURCE_DIR}"
)

target_link_libraries(transceiver_properties_manager_test
    fboss_error
    transceiver_properties_manager
    Folly::folly
    ${GTEST}
    ${LIBGMOCK_LIBRARIES}
)

gtest_discover_tests(transceiver_properties_manager_test)
