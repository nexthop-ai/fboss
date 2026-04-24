# Shell snippet that loads the fboss_builder docker image if it is not
# already present. Prepend this to the `cmd` of any genrule / heavy_genrule
# that invokes the fboss builder, and list "//fboss:fboss_builder_docker"
# in that rule's srcs so $(location ...) resolves.
LOAD_FBOSS_BUILDER_CMD = """
        if ! docker images | grep -q fboss_builder; then
            cat $(location //fboss:fboss_builder_docker) | docker image load
        fi
"""

def fboss_unit_test(name, tags=None):
    native.sh_test(
        name = "unittest-" + name,
        srcs = ["fboss/oss/scripts/bazel_test.sh"],
        args = [name],
        data = [
            ":run_in_builder",
            "//fboss:fboss_builder.tar",
            ":" + name,
        ],
        tags = tags,
    )
