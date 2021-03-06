#!/bin/sh
# Ensure everyone is a member of "developer" group
/usr/sbin/dseditgroup -o edit -a everyone -t group _developer

# Enable Developer Mode
/usr/sbin/DevToolsSecurity -enable

# Accept the license
/Applications/%fixed_filename%/Contents/Developer/usr/bin/xcodebuild -license accept

# Install embedded packages
for PKG in $(/bin/ls /Applications/%fixed_filename%/Contents/Resources/Packages/*.pkg); do
    /usr/sbin/installer -pkg "$PKG" -target /
done