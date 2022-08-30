#!/bin/bash
# Script based off jamf_ea_BetaSeed.sh by Zack Thompson
# Co-opted by James Smith - james@smithjw.me

SEEDUTIL="/System/Library/PrivateFrameworks/Seeding.framework/Resources/seedutil"
SEED="${4}"

if [[ -e "${SEEDUTIL}" ]]; then

    if "${SEEDUTIL}" enroll "${SEED}" 2>&1 | grep -q 'Enrollment was successful'; then
        echo "Enrolment Success"
    else
        echo "Enrolment Failed"
        exit 1
    fi

else
    echo "seedutil not found"
    exit 1
fi

exit 0
