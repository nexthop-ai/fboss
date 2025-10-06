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
