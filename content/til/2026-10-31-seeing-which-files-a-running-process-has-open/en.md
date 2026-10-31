Title: Seeing which files a running process has open
Description: /proc/<pid>/fd, a live view of what a silent process is doing
Tags: [linux, proc, borg, claude]

I asked Claude how a long Borg backup was going. The job didn't report any progress, yet Claude told me which folder it was reading. I asked how it knew, and learned about `/proc/<pid>/fd`.

Linux exposes every running process as a `/proc/<pid>` directory. Its `fd` subdirectory holds one symbolic link per open file descriptor, pointing at what the descriptor is open on:

```bash
$ pgrep -f "borg create"
14142

$ sudo ls -l /proc/14142/fd
lr-x------ 1 root root 64 Oct 31 15:55 0 -> /dev/null
l-wx------ 1 root root 64 Oct 31 15:55 1 -> pipe:[1745378]
l-wx------ 1 root root 64 Oct 31 15:55 2 -> pipe:[1745378]
lr-x------ 1 root root 64 Oct 31 15:55 3 -> /srv/drive
lr-x------ 1 root root 64 Oct 31 15:55 8 -> /srv/drive/photos
lr-x------ 1 root root 64 Oct 31 15:55 10 -> /srv/drive/photos/2022
lr-x------ 1 root root 64 Oct 31 16:00 13 -> /srv/drive/photos/2022/PXL_20220501_172832124.jpg
```

Descriptors 0, 1 and 2 are the usual stdin, stdout and stderr. Here the open directories show the path Borg walked down, and the last link is the file it is reading right now. `sudo` is only needed for processes of other users.

Next to it, `/proc/<pid>/fdinfo/<fd>` gives the current position in that file. Comparing it to the file's size tells how far along the process is, here at the very end:

```bash
$ sudo cat /proc/14142/fdinfo/13
pos:    4717661
flags:  03504000
mnt_id: 860
ino:    29234229

$ sudo stat -L -c %s /proc/14142/fd/13
4717661
```

It's only a snapshot, and it says nothing about the files left to read, but it's enough to tell a slow job from a stuck one. `lsof -p <pid>` shows the same information in a single table.
