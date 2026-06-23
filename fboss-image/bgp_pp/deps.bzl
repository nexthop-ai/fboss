load("//bazel_lib:s3_file.bzl", "s3_file")

# NOTE: The function name, repo rule name ("bgp_pp_tarball"), S3 path, and
# module extension name ("bgp_pp_deps") still use the old "bgp_pp" naming
# because the S3 artifact has not been renamed yet and MODULE.bazel (outside
# this repo) references these symbols.
# IMPORTANT: If you update the S3 path or sha256 here, also update
# fboss-image/bgpd/deps.bzl which is a standalone copy used by the nh
# MODULE.bazel migration to rename to bgpd.
def _bgp_pp_deps_impl(_):
    s3_file(
        name = "bgp_pp_tarball",
        s3_path = "s3://fboss-sai/bgp_pp/bgp_pp-1.0.tar.gz",
        filename = "bgp_pp-1.0.tar.gz",
        sha256 = "362ff4caecc51b7d646205cd989e028b65c436d5693ceb5fa6255687eb73fdc9",
    )

bgp_pp_deps = module_extension(
    implementation = _bgp_pp_deps_impl,
)
