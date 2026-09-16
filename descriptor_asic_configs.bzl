"""Checks the asic_config.yaml beside each platform descriptor against its generated source."""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

_PLATFORMS_DIR = "fboss/configs/platforms"
_COMPARE_SCRIPT = "//bazel_lib:generated_files_identical"
_REGISTRY_SCRIPT = "fboss/oss/scripts/descriptor_asic_config_registry.sh"

# descriptor: <vendor>/<platform> whose platform_mapping/generated holds platform_mapping.json,
#   which is where SaiBcmPlatform::getHwConfig() reads asic_config.yaml from at runtime.
# generated: the asic_config_v3 output the copy is taken from.
_DESCRIPTOR_COPIES = [
    struct(
        descriptor = "nexthop/m4062nhp",
        generated = "nexthop/m4062nhp/asic_config/generated/m4062nhp_default.yml",
        platform = "m4062nhp",
    ),
    struct(
        descriptor = "nexthop/m4062nhp_p1",
        generated = "nexthop/m4062nhp/asic_config/generated/m4062nhp_p1.yml",
        platform = "m4062nhp",
    ),
]

def _copy_path(descriptor):
    return _PLATFORMS_DIR + "/" + descriptor + "/platform_mapping/generated/asic_config.yaml"

def _generated_path(generated):
    return _PLATFORMS_DIR + "/" + generated

def _copy_diff_test(entry):
    """Diffs one descriptor copy against the generated yaml it comes from."""
    generated = _generated_path(entry.generated)
    copy = _copy_path(entry.descriptor)
    sh_test(
        name = entry.descriptor.replace("/", "_") + "-descriptor_asic_config",
        srcs = [_COMPARE_SCRIPT],
        args = [
            "$(location " + copy + ")",
            "$(location " + generated + ")",
            ("Stale. Regenerate with: ./fboss/lib/asic_config_v3/run-helper.sh " +
             "--platform {platform} && cp {generated} {copy}").format(
                platform = entry.platform,
                generated = generated,
                copy = copy,
            ),
        ],
        data = [copy, generated],
        size = "small",
    )

def _check_registry():
    """Adds a failing test when a descriptor ships a yaml this file does not cover."""
    covered = [_copy_path(e.descriptor) for e in _DESCRIPTOR_COPIES]
    uncovered = [
        f
        for f in native.glob([_PLATFORMS_DIR + "/*/*/platform_mapping/generated/asic_config.yaml"], allow_empty = True)
        if f not in covered
    ]

    sh_test(
        name = "descriptor_asic_config_registry",
        srcs = [_REGISTRY_SCRIPT],
        args = uncovered,
        size = "small",
    )

def register_descriptor_asic_config_tests():
    """Registers all descriptor asic_config.yaml tests. Call once from fboss/BUILD.bazel."""
    for entry in _DESCRIPTOR_COPIES:
        _copy_diff_test(entry)

    _check_registry()

    native.test_suite(
        name = "descriptor_asic_config_tests",
        tests = [
            ":" + e.descriptor.replace("/", "_") + "-descriptor_asic_config"
            for e in _DESCRIPTOR_COPIES
        ] + [":descriptor_asic_config_registry"],
    )
