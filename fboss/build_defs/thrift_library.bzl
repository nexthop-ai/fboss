"""Thrift library rule for FBOSS Bazel build.

Compiles .thrift files to C++ using the fbthrift compiler and produces
a cc_library with the generated code.
"""

load("@rules_cc//cc:defs.bzl", "cc_library")

# Thrift compiler from pre-built fbthrift (declared as a Bazel label so
# genrules properly depend on the fbthrift repository rule).
_THRIFT_COMPILER_LABEL = "@fbthrift//:bin/thrift1"

# Static include path for the fboss source tree
_FBOSS_INCLUDE = "/var/FBOSS/fboss"

# thrift1 resolves `include "..."` through -I /var/FBOSS/fboss, straight off
# the source tree, so the genrule below never sees the included .thrift files
# as inputs unless we hand them over explicitly. Without that, its action key
# is the same before and after an included file changes, and a shared remote
# cache serves generated code from the other version. This aspect walks a
# library's deps and gathers every .thrift file they compile, transitively.
_ThriftSourcesInfo = provider(
    doc = "The .thrift files a target and its dependencies compile.",
    fields = {"sources": "depset of File"},
)

def _collect_thrift_sources_impl(target, ctx):
    if _ThriftSourcesInfo in target:
        # A _thrift_sources rule already reports its own sources.
        return []
    direct = []
    transitive = []
    for attr_name in ("srcs", "deps"):
        values = getattr(ctx.rule.attr, attr_name, None)
        if type(values) != "list":
            continue
        for dep in values:
            if _ThriftSourcesInfo in dep:
                transitive.append(dep[_ThriftSourcesInfo].sources)
            else:
                direct.extend([f for f in dep[DefaultInfo].files.to_list() if f.extension == "thrift"])
    return [_ThriftSourcesInfo(sources = depset(direct, transitive = transitive))]

_collect_thrift_sources = aspect(
    implementation = _collect_thrift_sources_impl,
    attr_aspects = ["srcs", "deps"],
)

def _thrift_sources_impl(ctx):
    sources = depset(
        ctx.files.srcs,
        transitive = [
            dep[_ThriftSourcesInfo].sources
            for dep in ctx.attr.deps
            if _ThriftSourcesInfo in dep
        ],
    )
    return [DefaultInfo(files = sources), _ThriftSourcesInfo(sources = sources)]

_thrift_sources = rule(
    implementation = _thrift_sources_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = [".thrift"]),
        "deps": attr.label_list(aspects = [_collect_thrift_sources]),
    },
    doc = "This library's .thrift files plus those of every thrift library it depends on.",
)

def _thrift_gen_type_files(name):
    """Return the type-related files generated for a .thrift file."""
    prefix = "gen-cpp2/" + name
    return [
        prefix + "_constants.cpp",
        prefix + "_constants.h",
        prefix + "_data.cpp",
        prefix + "_data.h",
        prefix + "_metadata.cpp",
        prefix + "_metadata.h",
        prefix + "_types.cpp",
        prefix + "_types.h",
        prefix + "_types.tcc",
        prefix + "_types_fwd.h",
        prefix + "_types_custom_protocol.h",
        prefix + "_types_binary.cpp",
        prefix + "_types_compact.cpp",
        prefix + "_types_serialization.cpp",
        prefix + "_sinit.cpp",
        prefix + "_clients.h",
        prefix + "_clients_fwd.h",
        prefix + "_handlers.h",
    ]

def _thrift_gen_service_files(service_name):
    """Return the service-related files generated for a thrift service."""
    prefix = "gen-cpp2/" + service_name
    return [
        prefix + ".cpp",
        prefix + ".h",
        prefix + ".tcc",
        prefix + "AsyncClient.cpp",
        prefix + "AsyncClient.h",
        prefix + "_custom_protocol.h",
        prefix + "_processmap_binary.cpp",
        prefix + "_processmap_compact.cpp",
    ]

def fboss_thrift_library(
        name,
        thrift_srcs,
        services = [],
        deps = [],
        thrift_cpp2_options = "",
        visibility = None):
    """Generate a C++ library from .thrift files.

    Args:
        name: Target name
        thrift_srcs: Either a list of .thrift files (no services) or a dict
            mapping .thrift files to lists of service names, e.g.:
            {"ctrl.thrift": ["FbossCtrl"], "config.thrift": []}
        services: (deprecated) Flat list of services, only used with list-form thrift_srcs
        deps: Dependencies (other thrift libraries or cc_libraries)
        thrift_cpp2_options: Comma-separated options for mstch_cpp2 generator
        visibility: Visibility specification
    """
    gen_rules = []
    cc_srcs = []

    # Normalize thrift_srcs to dict form: {"file.thrift": [services]}
    if type(thrift_srcs) == type({}):
        srcs_dict = thrift_srcs
    else:
        # List form -- pair with flat services list (all services on first file)
        srcs_dict = {}
        for i, tf in enumerate(thrift_srcs):
            srcs_dict[tf] = services if i == 0 else []

    sources_name = name + "_thrift_sources"
    _thrift_sources(
        name = sources_name,
        srcs = srcs_dict.keys(),
        deps = deps,
        visibility = ["//visibility:public"],
    )

    for thrift_file, file_services in srcs_dict.items():
        base = thrift_file.replace(".thrift", "")
        gen_name = name + "_" + base + "_gen"

        # Collect output files: types for this file + services defined in it
        outputs = _thrift_gen_type_files(base)
        for svc in file_services:
            outputs.extend(_thrift_gen_service_files(svc))

        gen_options = thrift_cpp2_options if thrift_cpp2_options else "json"

        cmd = (
            "$(location " + _THRIFT_COMPILER_LABEL + ")" +
            " --gen mstch_cpp2:" + gen_options +
            " -I " + _FBOSS_INCLUDE +
            " -I $$(dirname $(location " + _THRIFT_COMPILER_LABEL + "))/../include" +
            " -o $(RULEDIR)" +
            " $(location " + thrift_file + ")"
        )

        native.genrule(
            name = gen_name,
            srcs = [thrift_file, ":" + sources_name],
            outs = outputs,
            cmd = cmd,
            tools = [_THRIFT_COMPILER_LABEL],
            visibility = ["//visibility:private"],
        )

        gen_rules.append(gen_name)
        cc_srcs.append(":" + gen_name)

    # Add fbthrift and folly runtime deps, avoiding duplicates
    all_deps = list(deps)
    for d in ["@fbthrift//:fbthrift", "@folly//:folly"]:
        if d not in all_deps:
            all_deps.append(d)

    cc_library(
        name = name,
        srcs = cc_srcs,
        deps = all_deps,
        copts = [
            "-I$(GENDIR)",
        ],
        visibility = visibility or ["//visibility:public"],
    )
