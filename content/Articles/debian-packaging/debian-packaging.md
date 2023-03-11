* https://wiki.debian.org/Python/GitPackaging
** Git branches
*** debian/master pristine-tar upstream
** gbp
* apt install devscripts
* uscan
** debian/watch mode=git
** uscan --verbose  --force-download
* changelog
** export EMAIL=charles...
** dch --create
* https://wiki.debian.org/Python/GitPackaging#Creating_a_new_package
* debian/control
** What are shlibs:Depends ?
** how to know latest debhelper-compat ?
** https://www.debian.org/doc/debian-policy/ch-controlfields.html
** Standards-Version: https://www.debian.org/doc/debian-policy/
** Lintian ?
* sbuild
** apt install sbuild sbuild-debian-developer-setup
** sudo sbuild-debian-developer-setup
*** newgrp sbuild
*** Apt-Cacher NG
**** How to clean cache ?
* debian/rules
** chmod a+x, it's a script

* Arch independant ???
* Sign git tag
* Mentors ?

