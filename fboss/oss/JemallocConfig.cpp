// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

// jemalloc reads this symbol during its own initialization; nothing in the
// binary references it. Linkers that run --gc-sections therefore discard it
// -- unless the binary also links --export-dynamic, which promotes it to a
// GC root and hides the problem. `used` keeps the compiler from dropping the
// definition and `retain` (SHF_GNU_RETAIN) keeps the linker from collecting
// its section, so the defaults apply whichever way a binary is linked.
extern "C" {
__attribute__((used, retain)) const char* malloc_conf =
    "background_thread:true,"
    "metadata_thp:auto,"
    "dirty_decay_ms:1000,"
    "muzzy_decay_ms:0";
}
