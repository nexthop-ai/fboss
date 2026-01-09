# Instructions

- Do not pipe commands to head/tail/grep etc, redirect the output to a /tmp file and then check $? to see if the command succeeded and then filter the output by running head/tail/grep etc on the /tmp file.

## Building and testing

- To build the code, don't invoke cmake directly, use this script: ./fboss/oss/scripts/nhfboss-build.sh
- To build a specific target use ./fboss/oss/scripts/nhfboss-build.sh --cmake-target <name>
- If the build fails with SAI_EXPERIMENTAL_INCLUDE_DIR-NOTFOUND you need a one-time initialization step for this workspace: ./fboss/oss/scripts/build-helper.py /var/extras/sai/1.16.1 /var/extras/sai/1.16.1 /var/extras/sai/1.16.1 1.16.1 --skip-archive-creation
- If there are issues with missing dependencies, you need to run ./fboss/oss/scripts/nhfboss-get-deps.sh and then retry running ./fboss/oss/scripts/nhfboss-build.sh
- You never need to manually build or delete anything under /var/FBOSS/tmp_bld_dir/
- To run the tests, use this script: ./fboss/oss/scripts/nhfboss-test.sh --timeout 30 --retry 0
- To run a subset of the tests, additionally pass --filter <regexp> where the regexp is matching the test case name in the code, not the cmake target.
- Always rebuild the code and the test binary and re-run unit tests to check your work.
- This project uses both cmake and BUCK, however we cannot build it with BUCK. Changes made to cmake files must also be reflected in the corresponding BUCK files, even though we cannot test them.

## Coding rules

- Use fmt::format instead of doing string concatenation.
- Don't use libc or stdlib functions that are not reentrant or thread safe. For example use folly::errnoStr() instead of strerror().
- Don't use std::regex, use RE2 instead.
- Whenever possible use existing strong typedefs from fboss/agent/types.h especially for things like interface IDs, port IDs, vlan IDs, etc.
- If possible avoid calling c_str() on std::string if not needed, in particular when passing it as a folly::StringPiece.
- Don't use .has_value() on Thrift non-optional fields.
- If a function may return a nullable pointer, it must be marked nullable by annotating the return type with FOLLY_NULLABLE defined in <folly/CppAttributes.h>.
