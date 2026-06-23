# Temporary shim — allows nh/MODULE.bazel to migrate from
# //fboss/fboss-image/bgp_pp:deps.bzl to //fboss/fboss-image/bgpd:deps.bzl
# without a chicken-and-egg CI breakage. Remove this directory once
# fboss-image/bgp_pp/ is deleted as part of renaming to bgpd.

load("//bazel_lib:s3_file.bzl", "s3_file")

def _bgpd_deps_impl(_):
    s3_file(
        name = "bgp_pp_tarball",
        s3_path = "s3://fboss-sai/bgp_pp/bgp_pp-1.0.tar.gz",
        filename = "bgp_pp-1.0.tar.gz",
        sha256 = "362ff4caecc51b7d646205cd989e028b65c436d5693ceb5fa6255687eb73fdc9",
    )

bgpd_deps = module_extension(
    implementation = _bgpd_deps_impl,
)
