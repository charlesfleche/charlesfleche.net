Title: Removing a folder in every borg archive
Description: Removing a folder in every borg archive

A bunch of folders should not have been included into borg archive. Fortunately, borg allows to remove those is two steps:

```sh
# Assuming BORG_* environment variables are set

borg recreate --exclude 'path/to/folder1' --exclude 'path/to/folder2'
borg compact
```

