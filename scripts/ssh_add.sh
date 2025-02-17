#!/bin/bash

# This script is intended for running the app on a Windows host,
# where the ssh key that's mounted in the container will have
# permissions that are too open.

eval "$(ssh-agent -s)"
find ~/.ssh/ -name id_* ! -name \"*.*\" | head -n 1 | xargs cat | ssh-add -k -