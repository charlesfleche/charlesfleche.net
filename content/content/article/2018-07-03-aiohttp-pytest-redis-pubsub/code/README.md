# Testing Redis PUB/SUB in Python / aiohttp with pytest

``` shell
$ vagrant up # Spin a debian box with Redis and Python3
$ vagrant ssh
$ cd /vagrant
$ python3 -m venv env
$ source env/bin/activate
$ pip install wheel
$ pip install -r requirements.txt
$ pytest
```
