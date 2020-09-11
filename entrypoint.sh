#!/usr/bin/env bash
# set -e

if [ "$#" -le 1 ]; then
    echo "You must provide a WORKDIR and COMMAND"
    exit 1
fi

workdir="$1"
commands="${@:2}"

cd /

# export PATH="/opt/conda/envs/tasks/bin:$PATH"

inv -f ${workdir}/invoke.yml ${commands} > /output.txt

semester=$(grep -i semester ${workdir}/invoke.yml | cut -d " " -f 2)

status=$(cat /output.txt)
status=${status//'%'/'%25'}
status=${status//$'\n'/'%0A'}
status=${status//$'\r'/'%0D'}

exitcodes=$(echo ${status} | grep "Please add them" -c)

echo "::set-output name=status::${status}"
echo "::set-output name=semester::${semester}"
echo "::set-output name=exitcode::${exitcodes}"