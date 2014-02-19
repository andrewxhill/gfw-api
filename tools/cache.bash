##!/bin/bash

MINX="5752"
MINY="3649"
MAXX="5756"
MAXY="3657"
Z="6"

URL="http://gfw-apis.appspot.com/gee/landsat_composites/"

for x in `seq $MINX $MAXX`
do
  for y in `seq $MINY $MAXY`
  do    
    curl -I `echo -n "${URL}${Z}/${x}/${y}.png"
  done
done