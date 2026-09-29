load("@rules_shell//shell:sh_test.bzl", "sh_test")
load("//bazel_lib:heavy_genrule.bzl", "heavy_genrule")

# Shell snippet that selects the build region when the CI passes one with
# --action_env=NH_CLOUD_PROVIDER=<region>. Without it the links written by an
# earlier selection stay in place; there is no default. No `$` here, so it
# works in genrule and heavy_genrule alike.
SELECT_REGION_CMD = """
        fboss/fboss/oss/scripts/set-region.sh --from-env
"""

# Shell snippet that loads the fboss_builder docker image if it is not
# already present. flock serializes concurrent genrules loading the same
# image, like image compositions. /var/tmp is outside the sandbox.
_LOAD_IMAGE_CMD = """
        if ! docker images | grep -q fboss_builder; then
            (
                flock 9
                if ! docker images | grep -q fboss_builder; then
                    cat $(location //fboss:fboss_builder_docker) | docker image load
                fi
            ) 9>/var/tmp/.fboss_builder_load.lock
        fi
"""

# Region selection + image load, for the no-sandbox builder genrules. Prepend
# to the `cmd` of any heavy_genrule that invokes the fboss builder, and list
# "//fboss:fboss_builder_docker" in that rule's srcs so $(location ...)
# resolves. Sandboxed compositions use _LOAD_IMAGE_CMD instead: set-region.sh
# is not among their inputs and writes to the source tree, which a sandbox
# mounts read-only, so distro_build makes their region links in the sandbox .
LOAD_FBOSS_BUILDER_CMD = SELECT_REGION_CMD + _LOAD_IMAGE_CMD

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

# Snippet that sets shell var $free_up_disk_arg to "--free-up-disk" on a CI
# build (numeric BUILD_ID in volatile-status.txt), else "". Prepend to a genrule
# cmd, then inject "${free_up_disk_arg}" into the build_fboss_stack.sh argv so
# getdeps drops each dep's build/ after install (lowers peak disk in CI; dev
# keeps intermediates). Same CI gate as delete_build_products_in_ci.
# (heavy_genrule expands cmd via ctx.expand_location, which does NOT reduce
# $$ to $ like native genrule -- use a single $ for shell expansion.)
FREE_UP_DISK_IN_CI_CMD = """
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
        tags = (tags or []) + ["resources:docker_test_clients:1"],
    )

# Marker in `execute` that becomes "--free-up-disk" on CI builds and disappears elsewhere.
FREE_UP_DISK = "{free_up_disk}"

# jq: write `execute` (and `artifact`) for $component, resolving FREE_UP_DISK against $fud.
_COMPONENT_FILTER = (
    '($execute | if type == "array" then map(if . == "%s" then $fud else . end) | map(select(. != "")) else . end) as $exec' % FREE_UP_DISK +
    ' | ({"execute": $exec} + (if $artifact == "" then {} else {"artifact": $artifact} end)) as $entry' +
    ' | .[$component] = (if $list then [$entry] else $entry end)'
)

# Absolute so distro_build() works from any package that builds through the fboss builder.
_TOOLS = [
    "//bazel_lib:ln_or_cp",
    "//fboss:fboss_builder_docker",
    "//fboss/fboss-image/distro_cli:builder",
    "//fboss:nh-fboss-manifests",
]

# Manifest components that hold a list of entries rather than a single one.
_LIST_COMPONENTS = ["bsps", "other_dependencies"]

# Resource sets that saturate the machine, so no other distro_build action runs alongside.
_SERIALIZED = ["exclusive", "all_cpus"]

_IMAGE_BUILDER = "fboss/fboss-image/image_builder"

# Build products, excluded from //fboss:image_builder, so a sandboxed action starts
# without them. kiwi's own scratch ("root") is excluded there too and it recreates it.
_IMAGE_BUILDER_SCRATCH = ["deps_staging", "output", "logs"]

_BUILD_INFO = "%s/templates/centos-09.0/root_files/etc/nexthop_build_info" % _IMAGE_BUILDER

_BUILDER_IMAGE_SOURCES = [
    "//fboss:fboss/oss/docker/Dockerfile",
    "//fboss:fboss/oss/scripts/build_docker.sh",
]

# volatile-status keys every image records in /etc/nexthop_build_info.
_BUILD_INFO_COMMON_KEYS = [
    "BUILD_ID",
    "GIT_COMMIT_NH",
    "GIT_COMMIT_FBOSS",
    "GIT_COMMIT_BGP",
]

def _basename(label):
    return label.split(":")[-1].split("/")[-1]

def distro_build(
        name,
        manifest,
        outs_map,
        deps = [],
        srcs = [],
        component = None,
        execute = None,
        artifact = None,
        setup = "",
        manifest_edits = None,
        nexthop_build_info = None,
        cleanup = [],
        needs = "exclusive",
        tags = [],
        visibility = None):
    """Runs `fboss-image build` for one manifest and copies the results into Bazel outputs.

    Args:
        name: Target name.
        manifest: Manifest file name in fboss-image/, e.g. "nh-fboss-broadcom-xgs.json". It must be
            listed in //fboss:nh-fboss-manifests, which is how it reaches the action.
        outs_map: dict {output file: path the builder leaves it at, relative to the execroot}. An
            output ending in ".zst" whose source does not is compressed with zstd instead of copied.
        deps: Artifact labels the manifest downloads. Each is hardlinked into this target's
            scratch directory under its basename, and the manifest's `file:` URL for that basename
            is rewritten to match.
        srcs: Other inputs that are not staged (source filegroups, cmake files, hook manifests).
        component: Component passed to `fboss-image build`; None builds the whole image.
        execute: Command to run for `component` instead of the manifest's entry: an argv list or a
            single script path string. FREE_UP_DISK in a list becomes "--free-up-disk" on CI builds
            and is dropped otherwise. For `bsps` and `other_dependencies` the entry is written as
            the component's one-element list.
        artifact: `artifact` field of the component entry, for components whose build leaves a file
            the builder has to pick up by name (RPMs under other_dependencies).
        setup: Shell snippet run after staging and before the build, for inputs the component's
            script expects in the source tree rather than the staging directory.
        manifest_edits: Extra jq filter applied to the manifest. `$stage` holds this target's
            scratch directory relative to the manifest, for `file:` URLs written by the filter.
        nexthop_build_info: {"image_type": str, "keys": [volatile-status keys]} written to
            /etc/nexthop_build_info in the image; images only. BUILD_ID, GIT_COMMIT_NH,
            GIT_COMMIT_FBOSS and GIT_COMMIT_BGP are always recorded, `keys` adds the
            platform-specific ones.
        cleanup: Execroot-relative paths private to this action, removed after a CI build along
            with the scratch directory. distro_cli/.artifacts is shared and is removed only by
            actions whose `needs` saturates the machine, since a smaller action may run alongside
            another one that is still reading it.
        needs: heavy_genrule resource set.
        tags: Extra tags
        visibility: Target visibility.
    """
    stem = manifest.removesuffix(".json")
    stage_dir = "%s/.distro_build/%s" % (native.package_name(), name)
    stage = "../../" + stage_dir  # relative to fboss/fboss-image, where the manifest is read
    is_image_composition = component == None

    # A composition runs sandboxed so it can run concurrently. FBOSS_ROOT stops
    # the CLI resolving __file__ back to the real checkout, escaping the sandbox.
    # tar makes the sandbox files real instead of symlinks, which docker can't
    # use. The region links are build state, not inputs, so the sandbox starts
    # without them: recreate them here from NH_CLOUD_PROVIDER (//fboss:region_config
    # provides the regions/ files, and the links too when one was selected).
    prepare = ""
    if is_image_composition:
        prepare = """
        export FBOSS_ROOT="${{PWD}}/fboss"
        tar -chf "{tarball}" -C {src} .
        tar -xf "{tarball}" -C {src}
        rm -f "{tarball}"
        mkdir -p {scratch}

        if [ -n "${{NH_CLOUD_PROVIDER:-}}" ]; then
            if [ ! -f "fboss/fboss/oss/scripts/regions/${{NH_CLOUD_PROVIDER}}.env" ]; then
                echo "distro_build: unknown region '${{NH_CLOUD_PROVIDER}}'" >&2
                exit 1
            fi
            ln -sfn "regions/${{NH_CLOUD_PROVIDER}}.env" fboss/fboss/oss/scripts/region.env
            ln -sfn "regions/local_mirror.${{NH_CLOUD_PROVIDER}}.repo" fboss/fboss/oss/scripts/region.repo
        elif [ ! -e fboss/fboss/oss/scripts/region.env ]; then
            echo "ERROR: no build region selected; pass --action_env=NH_CLOUD_PROVIDER=<region>" >&2
            exit 1
        fi
        """.format(
            src = _IMAGE_BUILDER,
            tarball = "%s/image_builder.tar" % stage_dir,
            scratch = " ".join(['"%s/%s"' % (_IMAGE_BUILDER, name) for name in _IMAGE_BUILDER_SCRATCH]),
        )
    patched = "%s.%s.generated.json" % (native.package_name().replace("/", "_"), name)

    basenames = [_basename(dep) for dep in deps]
    filters = []
    if deps:
        filters.append(
            'walk(if type == "string" and startswith("file:") then ((split("/") | last) as $b' +
            ' | if ($staged | index($b)) != null then "file:" + $stage + "/" + $b else . end) else . end)',
        )
    filters.append(manifest_edits or ".")
    jq_args = ['--arg stage "%s"' % stage, '--arg fud "${free_up_disk_arg}"', "--argjson staged '%s'" % json.encode(basenames)]
    if execute != None or artifact != None:
        if component == None:
            fail("distro_build(%s): execute/artifact need a component" % name)
        jq_args += [
            '--arg component "%s"' % component,
            "--argjson execute '%s'" % json.encode(execute),
            '--arg artifact "%s"' % (artifact or ""),
            "--argjson list %s" % ("true" if component in _LIST_COMPONENTS else "false"),
        ]
        filters.append(_COMPONENT_FILTER)

    staging = "\n        ".join([
        'ln -f $(location %s) "%s/%s"' % (dep, stage_dir, _basename(dep))
        for dep in deps
    ])

    info = ""
    if nexthop_build_info:
        keys = _BUILD_INFO_COMMON_KEYS + [k for k in nexthop_build_info.get("keys", []) if k not in _BUILD_INFO_COMMON_KEYS]
        info = """
        mkdir -p "{dir}"
        echo "IMAGE_TYPE {image_type}" > "{path}"
        grep {keys} bazel-out/volatile-status.txt >> "{path}"
        """.format(
            dir = _BUILD_INFO.rsplit("/", 1)[0],
            path = _BUILD_INFO,
            image_type = nexthop_build_info["image_type"],
            keys = " ".join(["-e '%s '" % key for key in keys]),
        )

    copies = []
    for out, src in outs_map.items():
        if out.endswith(".zst") and not src.endswith(".zst"):
            copies.append("zstd -T0 -12 -f -o $(location %s) %s" % (out, src))
        else:
            copies.append("$(execpath //bazel_lib:ln_or_cp) %s $(location %s)" % (src, out))

    cmd = (_LOAD_IMAGE_CMD if is_image_composition else LOAD_FBOSS_BUILDER_CMD) + FREE_UP_DISK_IN_CI_CMD + """
        mkdir -p "{stage_dir}"
        {prepare}
        {staging}
        {setup}
        {info}
        pushd fboss/fboss-image
        jq {jq_args} '{filter}' {stem}.json > {patched}
        ./distro_cli/fboss-image build {patched} {component} 2>&1
        popd

        {copies}
    """.format(
        stage_dir = stage_dir,
        prepare = prepare,
        staging = staging,
        setup = setup,
        info = info,
        jq_args = " ".join(jq_args),
        filter = " | ".join(filters),
        stem = stem,
        patched = patched,
        component = component or "",
        copies = "\n        ".join(copies),
    )
    # Image compositions are sandboxed. Component builds are not for speed.
    action_tags = ["requires-network"] if is_image_composition else ["no-sandbox"]

    shared = [] if is_image_composition else (["fboss/fboss-image/distro_cli/.artifacts"] if needs in _SERIALIZED else [])
    cmd += delete_build_products_in_ci([stage_dir] + cleanup + shared)

    heavy_genrule(
        name = name,
        stamp = True,
        needs = needs,
        srcs = _TOOLS + ((["//fboss:image_builder", "//fboss:region_config"] + _BUILDER_IMAGE_SOURCES) if is_image_composition else []) + deps + srcs,
        outs = outs_map.keys(),
        cmd = cmd,
        tags = action_tags + tags,
        visibility = visibility,
    )
