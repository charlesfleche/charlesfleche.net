#!/bin/bash

exiftool -m '-filename<GPSDateTime' '-filename<CreateDate' '-filename<DateTimeOriginal' -d "%Y%m%d-%H%M%S.%%le" .
