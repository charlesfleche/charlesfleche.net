#!/bin/bash

exiftool '-filename<DateTimeOriginal' -d %Y%m%d-%H%M%S.jpg .

