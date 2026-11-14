Title: Deleted files in /proc/<pid>/maps
Description: Libraries replaced by an upgrade, and a lot of memfd shared memory
Tags: [linux, proc, memfd, claude]

`/proc/<pid>/maps` lists everything a process has mapped in memory: its executable, its libraries, its shared memory. When a mapped file is removed from disk, the process keeps the old content and the kernel appends `(deleted)` to its path:

```bash
$ grep '(deleted)' /proc/[0-9]*/maps
7f927e800000-7f927e88d000 r--p 00000000 fd:00 13369453    /opt/Signal/libffmpeg.so (deleted)
7f55f23ef000-7f55f23f6000 r--s 00000000 00:01 2115        /memfd:mozilla-ipc (deleted)
```

The first line is Signal still running the `libffmpeg.so` from before its upgrade: it needs a restart.

The second one is not a stale file. `memfd_create()` creates an anonymous file that only lives in RAM, used to share memory between processes, here by Firefox. It never had a name on disk, so the kernel always shows it as deleted.

Filtering the memfd out leaves the files that were really replaced:

```bash
$ grep -h '(deleted)' /proc/[0-9]*/maps | awk '{print $6}' | grep -v '^/memfd:' | sort | uniq -c | sort -rn | head -2
     30 /opt/Signal/signal-desktop
     28 /opt/Signal/libffmpeg.so
```
