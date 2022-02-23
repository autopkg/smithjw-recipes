#!/bin/sh

# Add version number to Xcode name if present
if [ -n "$4" ]; then
    xcode_app="Xcode-$4"
fi

# Ensure everyone is a member of "developer" group
/usr/sbin/dseditgroup -o edit -a everyone -t group _developer

# Enable Developer Mode
/usr/sbin/DevToolsSecurity -enable

# Make sure any quarantine files are removed
/usr/bin/xattr -d com.apple.quarantine /Applications/"$xcode_app".app

# Switch to new Xcode Version
/usr/bin/xcode-select -s /Applications/"$xcode_app".app

# Accept the license
/Applications/"$xcode_app".app/Contents/Developer/usr/bin/xcodebuild -license accept

# Install embedded packages
for PKG in $(/bin/ls /Applications/"$xcode_app".app/Contents/Resources/Packages/*.pkg); do
    /usr/sbin/installer -pkg "$PKG" -target /
done