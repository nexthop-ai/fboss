"""Checks that committed agent.conf files match generate_distro_bootstrap_agent_config.py output."""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

_SCRIPTS_DIR = "fboss/oss/scripts"
_GENERATOR = _SCRIPTS_DIR + "/generate_distro_bootstrap_agent_config.py"
_COMPARE_SCRIPT = "//bazel_lib:generated_files_identical"
_REGISTRY_SCRIPT = _SCRIPTS_DIR + "/bootstrap_agent_config_registry.sh"
_CONFIGS_DIR = _SCRIPTS_DIR + "/run_configs/default_configs"
_PLATFORMS_DIR = "fboss/lib/platform_mapping_v2/platforms"
_HW_TEST_CONFIGS_DIR = "fboss/oss/hw_test_configs"

# Stands in for platforms with no ASIC config, so --asic-config-source is always
# passed. Without it the generator auto-detects hw_test_configs/ relative to its
# own __file__, which resolves out of the sandbox and reads undeclared inputs.
_EMPTY_ASIC_CONFIG = ":empty_asic_config"

# mapping_codename: platform_mapping_v2 dir supplying the CSVs, when it differs
#   from platform (minipack3 -> montblanc; wedge800bnhp borrows wedge800bact's).
# asic_codename: hw_test_configs materialized JSON, when it differs from
#   platform. None means the platform has no ASIC config.
_GENERATED_PLATFORMS = [
    struct(platform = "m4062nhp", mapping_codename = None, asic_codename = "m4062nhp"),
    struct(platform = "minipack3", mapping_codename = "montblanc", asic_codename = "montblanc"),
    struct(platform = "nh4010f", mapping_codename = None, asic_codename = "nh4010f"),
    struct(platform = "nh4220f", mapping_codename = None, asic_codename = "nh4220f"),
    struct(platform = "wedge800bact", mapping_codename = None, asic_codename = "wedge800bact"),
    struct(platform = "wedge800cact", mapping_codename = None, asic_codename = "wedge800cact"),
]

# NHP and ACT are the same product from different vendors, so their configs must
# stay byte-identical.
_IDENTITY_PLATFORMS = [
    struct(platform = "wedge800bnhp", source_platform = "wedge800bact"),
    struct(platform = "wedge800cnhp", source_platform = "wedge800cact"),
]

_EXCLUDED_PLATFORMS = [
    "cfboss",  # hand-authored fake-SAI config, no platform_mapping_v2 entry
    "nh5010f",  # hand-authored while dataplane bring-up is in progress
]

def _committed_conf(platform):
    return _CONFIGS_DIR + "/" + platform + "/agent.conf"

def _conf_diff_test(name, actual, expected, hint):
    sh_test(
        name = name,
        srcs = [_COMPARE_SCRIPT],
        args = [
            "$(location " + actual + ")",
            "$(location " + expected + ")",
            hint,
        ],
        data = [actual, expected],
        size = "small",
    )

def _bootstrap_agent_config_test(platform, mapping_codename, asic_codename):
    """Regenerates one platform's agent.conf and diffs it against the committed copy."""
    mapping_codename = mapping_codename or platform
    platform_dir = _PLATFORMS_DIR + "/" + mapping_codename
    ppm_csv = platform_dir + "/" + mapping_codename + "_port_profile_mapping.csv"
    static_csv = platform_dir + "/" + mapping_codename + "_static_mapping.csv"

    if asic_codename:
        asic_src = _HW_TEST_CONFIGS_DIR + "/" + asic_codename + ".agent.materialized_JSON"
    else:
        asic_src = _EMPTY_ASIC_CONFIG

    generated_out = "bootstrap_agent_configs/" + platform + "/agent.conf"

    native.genrule(
        name = platform + "-bootstrap_agent_conf",
        srcs = [ppm_csv, static_csv, asic_src],
        outs = [generated_out],
        cmd = """
        PPM=$(location {ppm_csv})
        python3 $(location {generator}) \\
            --platform {mapping_codename} \\
            --platforms-dir $$(dirname $$(dirname $$PPM)) \\
            --asic-config-source $(location {asic_src}) \\
            --output $@
        """.format(
            ppm_csv = ppm_csv,
            generator = _GENERATOR,
            mapping_codename = mapping_codename,
            asic_src = asic_src,
        ),
        tools = [_GENERATOR],
    )

    _conf_diff_test(
        platform + "-committed_bootstrap_agent_conf",
        generated_out,
        _committed_conf(platform),
        ("Stale. Regenerate with: bazel build //fboss:{platform}-bootstrap_agent_conf " +
         "&& cp bazel-bin/fboss/{out} {committed}").format(
            platform = platform,
            out = generated_out,
            committed = _committed_conf(platform),
        ),
    )

def _bootstrap_agent_config_identity_test(platform, source_platform):
    """Asserts platform's committed agent.conf is byte-identical to source_platform's."""
    _conf_diff_test(
        platform + "-identical_to_" + source_platform,
        _committed_conf(platform),
        _committed_conf(source_platform),
        ("{platform} and {source} are the same product from different vendors, so " +
         "their configs must match. Investigate the diff, do not edit either file " +
         "to silence this.").format(platform = platform, source = source_platform),
    )

def _has_own_mapping(platform):
    pattern = _PLATFORMS_DIR + "/" + platform + "/" + platform + "_port_profile_mapping.csv"
    return native.glob([pattern], allow_empty = True)

def _has_own_asic_config(platform):
    pattern = _HW_TEST_CONFIGS_DIR + "/" + platform + ".agent.materialized_JSON"
    return native.glob([pattern], allow_empty = True)

def _check_registry():
    """Adds a failing test when the registry no longer matches what is on disk."""
    generated = [p.platform for p in _GENERATED_PLATFORMS]
    known = generated + [p.platform for p in _IDENTITY_PLATFORMS] + _EXCLUDED_PLATFORMS
    problems = []

    for f in native.glob([_CONFIGS_DIR + "/*/agent.conf"], allow_empty = True):
        platform = f.split("/")[-2]
        if platform not in known:
            problems.append("uncovered:" + platform)

    # A borrowed mapping, or the empty ASIC stub, becomes obsolete once the
    # platform has its own.
    for p in _GENERATED_PLATFORMS:
        if p.mapping_codename and _has_own_mapping(p.platform):
            problems.append("own-mapping:" + p.platform)
        if not p.asic_codename and _has_own_asic_config(p.platform):
            problems.append("own-asic:" + p.platform)

    # An identity-only platform gaining inputs should be generated instead.
    for p in _IDENTITY_PLATFORMS:
        if p.platform in generated:
            continue
        if _has_own_mapping(p.platform):
            problems.append("own-mapping:" + p.platform)
        if _has_own_asic_config(p.platform):
            problems.append("own-asic:" + p.platform)

    sh_test(
        name = "bootstrap_agent_config_registry",
        srcs = [_REGISTRY_SCRIPT],
        args = problems,
        size = "small",
    )

def register_bootstrap_agent_config_tests():
    """Registers all bootstrap agent.conf tests. Call once from fboss/BUILD.bazel."""
    native.genrule(
        name = "empty_asic_config",
        outs = ["empty_asic_config.json"],
        cmd = """echo '{"platform":{"chip":{"asicConfig":{"common":{}}}}}' > $@""",
    )

    for p in _GENERATED_PLATFORMS:
        _bootstrap_agent_config_test(
            platform = p.platform,
            mapping_codename = p.mapping_codename,
            asic_codename = p.asic_codename,
        )
    for p in _IDENTITY_PLATFORMS:
        _bootstrap_agent_config_identity_test(
            platform = p.platform,
            source_platform = p.source_platform,
        )

    _check_registry()

    native.test_suite(
        name = "bootstrap_agent_config_tests",
        tests = [
            ":" + p.platform + "-committed_bootstrap_agent_conf"
            for p in _GENERATED_PLATFORMS
        ] + [
            ":" + p.platform + "-identical_to_" + p.source_platform
            for p in _IDENTITY_PLATFORMS
        ] + [":bootstrap_agent_config_registry"],
    )
