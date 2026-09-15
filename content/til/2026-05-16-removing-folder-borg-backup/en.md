Title: Removing a folder in every borg archive
Description: Removing a folder in every borg archive

A bunch of folders should not have been included in the borg archive. Fortunately, borg allows removing those in two steps:

```sh
# Assuming BORG_* environment variables are set

borg recreate --exclude 'path/to/folder1' --exclude 'path/to/folder2'
borg compact
```

