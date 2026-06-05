#!/usr/local/autopkg/python
#
# Copyright 2024 James Smith based on work by Allister Banks, & Hannes Juutilainen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import xml.etree.ElementTree as ET
from operator import itemgetter

from autopkglib import APLooseVersion, ProcessorError, URLGetter

__all__ = ["GlobalProtectVersionURLProvider"]

FEED_URL = "https://pan-gp-client.s3.amazonaws.com"


class GlobalProtectVersionURLProvider(URLGetter):
    """Provides the version and download URL for the Palo Alto Global Protect Client"""

    input_variables = {
        "feed_url": {"required": False, "description": f"Default is {FEED_URL}"},
        "version_search": {
            "required": False,
            "description": "Set the version you'd like to find for GlobalProtect (if left blank, defaults to latest)",
        },
    }
    output_variables = {
        "version": {"description": "Version number for this release of GlobalProtect"},
        "url": {"description": "URL for the found release of GlobalProtect"},
    }
    description = __doc__

    def fetch_gp_versions(self, feed_url):
        """Parse the Palo Alto S3 Bucket where GlobalProtect installers are hosted for the latest or defined version"""
        try:
            xml = self.download(feed_url)
        except Exception as e:
            raise ProcessorError(f"Can't download {feed_url}: {e}") from e

        ns = {"ns": "http://s3.amazonaws.com/doc/2006-03-01/"}
        root = ET.fromstring(xml)

        gp_version_array = [
            {
                "version": key.split("/")[0],
                "url": f"{feed_url}/{key}",
            }
            for content in root.findall("ns:Contents", ns)
            if (key := content.find("ns:Key", ns).text).endswith(".pkg")
        ]

        # # Extract specific version from each dict within in the list
        sorted_gp_version_array = sorted(
            gp_version_array, key=lambda a: APLooseVersion(a["version"]), reverse=True
        )

        self.output(f"GP Versions Found: {sorted_gp_version_array}", verbose_level=4)
        return sorted_gp_version_array

    def find_closest_version(self, gp_version_list, version_search):
        if not version_search:
            self.output("Version not set, looking for latest version", verbose_level=3)
            gp_version = max(gp_version_list, key=itemgetter("version"))
            return gp_version

        version_search = APLooseVersion(version_search)

        for gp_version in gp_version_list:
            version = APLooseVersion(gp_version["version"])
            if version == version_search:
                return gp_version

        # If exact match isn't found, find the highest version that matches
        matching_versions = [
            gp_version
            for gp_version in gp_version_list
            if gp_version["version"].startswith(version_search.vstring)
        ]

        if not matching_versions:
            matching_versions = [
                gp_version
                for gp_version in gp_version_list
                if gp_version["version"].startswith(
                    version_search.vstring.split("-", 1)[0]
                )
            ]

        if matching_versions:
            return max(matching_versions, key=lambda a: APLooseVersion(a["version"]))

        return max(gp_version_list, key=itemgetter("version"))

    def autopkg_output(self, name, value):
        self.env[name] = value
        self.output(f"Setting {name}: {value}")

    def main(self):
        feed_url = self.env.get("feed_url", FEED_URL)
        version_search = self.env.get("version_search", None)

        gp_version_list = self.fetch_gp_versions(feed_url)
        gp = self.find_closest_version(gp_version_list, version_search)

        self.autopkg_output("version", gp.get("version"))
        self.autopkg_output("url", gp.get("url"))


if __name__ == "__main__":
    processor = GlobalProtectVersionURLProvider()
    processor.execute_shell()
