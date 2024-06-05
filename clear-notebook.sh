#!/bin/bash
notebook=$1
echo "Clearing ${notebook}"
jupyter nbconvert --clear-output --inplace "${notebook}"
