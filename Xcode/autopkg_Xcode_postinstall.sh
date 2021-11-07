#!/bin/sh

# Enable Developer Mode
/usr/sbin/DevToolsSecurity -enable

# Accept the license
/Applications/Xcode-"$4".app/Contents/Developer/usr/bin/xcodebuild -license accept

# Install embedded packages
for PKG in $(/bin/ls /Applications/Xcode-"$4".app/Contents/Resources/Packages/*.pkg); do
    /usr/sbin/installer -pkg "$PKG" -target /
done