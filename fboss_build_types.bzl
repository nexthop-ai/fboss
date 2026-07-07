load("@rules_shell//shell:sh_test.bzl", "sh_test")

# Shell snippet that loads the fboss_builder docker image if it is not
# already present. Prepend this to the `cmd` of any genrule / heavy_genrule
# that invokes the fboss builder, and list "//fboss:fboss_builder_docker"
# in that rule's srcs so $(location ...) resolves.
LOAD_FBOSS_BUILDER_CMD = """
        if ! docker images | grep -q fboss_builder; then
            cat $(location //fboss:fboss_builder_docker) | docker image load
        fi
"""

def delete_build_products_in_ci(paths):
    """Snippet that deletes `paths` from the build scratch during a CI build.

    Args:
        paths: Non-empty list of paths passed to `rm -rf` (shell globs allowed).
            genrule cmds run at the execroot, so pass execroot-relative paths;
            this keeps the snippet reusable from packages outside //fboss.

    Returns:
        A shell snippet string compatible with heavy_genrule(). NOT compatible
        with genrule due to different $ escaping rules.
    """
    if not paths:
        fail("delete_build_products_in_ci: paths must be a non-empty list")
    return """
        if [ -f bazel-out/volatile-status.txt ]; then
            build_id="$(sed -n 's/^BUILD_ID //p' bazel-out/volatile-status.txt)"
            case "${{build_id}}" in
                ''|*[!0-9]*) ;;
                *)
                    echo "CI build ${{build_id}}: clearing intermediates from {paths}"
                    sudo rm -rf {paths} || true
                    ;;
            esac
        fi
""".format(paths = " ".join(paths))

def free_up_disk_in_ci():
    """Snippet that sets shell var $free_up_disk_arg to "--free-up-disk" on a CI
    build (numeric BUILD_ID in volatile-status.txt), else "". Prepend to a genrule
    cmd, then inject "${free_up_disk_arg}" into the build_fboss_stack.sh argv so
    getdeps drops each dep's build/ after install (lowers peak disk in CI; dev
    keeps intermediates). Same CI gate as delete_build_products_in_ci.
    (heavy_genrule expands cmd via ctx.expand_location, which does NOT reduce
    $$ to $ like native genrule -- use a single $ for shell expansion.)
    """
    return """
        free_up_disk_arg=""
        if [ -f bazel-out/volatile-status.txt ]; then
            build_id="$(sed -n 's/^BUILD_ID //p' bazel-out/volatile-status.txt)"
            case "${build_id}" in
                ''|*[!0-9]*) ;;
                *) free_up_disk_arg="--free-up-disk" ;;
            esac
        fi
"""

def fboss_unit_test(name, tags=None):
    sh_test(
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
