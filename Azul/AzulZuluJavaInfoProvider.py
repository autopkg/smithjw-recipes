#!/usr/local/autopkg/python
#
# Copyright 2022 David Pirie
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
"""See docstring for AzulZuluJavaInfoProvider class"""

import json

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

__all__ = ["AzulZuluJavaInfoProvider"]

DEFAULT_API_URL = "https://www.azul.com/wp-admin/admin-ajax.php?action=bundles&endpoint=community&use_stage=false&include_fields=java_version,openjdk_build_number,os,arch,bundle_type,javafx,latest,ext,name,sha256_hash,url"
DEFAULT_JAVA_MAJOR_VERSION = 7
DEFAULT_ARCH = "x86"
DEFAULT_EXTENSION = "dmg"
DEFAULT_BUNDLE_TYPE = "jre"

SUPPORTED_ARCHS = ["x86", "arm"]
SUPPORTED_EXTENSIONS = ["zip", "tar.gz", "dmg"]
SUPPORTED_BUNDLE_TYPES = ["jre", "jdk", "jre_fx", "jdk_fx"]

MUNKI_ARCHS = {"x86": "x86_64", "arm": "arm64"}


class AzulZuluJavaInfoProvider(URLGetter):
    """Provides URL to the latest Azul Zulu Java release."""

    description = __doc__
    input_variables = {
        "api_url": {
            "required": False,
            "description": f"URL for the api endpoint to {DEFAULT_API_URL}",
        },
        "java_major_version": {
            "required": False,
            "description": f"Major version of Java. Defaults to {DEFAULT_JAVA_MAJOR_VERSION}",
        },
        "arch": {
            "required": False,
            "description": f"Hardware architecture. Currently supports: {', '.join(SUPPORTED_ARCHS)}. Defaults to {DEFAULT_ARCH}.",
        },
        "extension": {
            "required": False,
            "description": f"Download file extension. Currently supports: {', '.join(SUPPORTED_EXTENSIONS)}. Defaults to {DEFAULT_EXTENSION}.",
        },
        "bundle_type": {
            "required": False,
            "description": f"Download bundle type. Currently supports: {', '.join(SUPPORTED_BUNDLE_TYPES)}. Defaults to {DEFAULT_BUNDLE_TYPE}.",
        },
    }
    output_variables = {
        "url": {"description": "URL to the latest Azul Zulu Java release."},
        "version": {"description": "Azul Zulu version."},
        "java_version": {"description": "Java version."},
        "openjdk_build_number": {"description": "OpenJDK build number."},
        "sha256_hash": {"description": "SHA256 hash for the download."},
        "munki_arch": {
            "description": "Architecture appropriate for the munki pkginfo key supported_architectures"
        },
    }

    def main(self):
        api_url = self.env.get("api_url", DEFAULT_API_URL)
        java_major_version = self.env.get(
            "java_major_version", DEFAULT_JAVA_MAJOR_VERSION
        )
        arch = self.env.get("arch", DEFAULT_ARCH)
        if arch not in SUPPORTED_ARCHS:
            raise ProcessorError(
                f"arch {arch} not one of those supported: {', '.join(SUPPORTED_ARCHS)}."
            )
        extension = self.env.get("extension", DEFAULT_EXTENSION)
        if extension not in SUPPORTED_EXTENSIONS:
            raise ProcessorError(
                f"extension {extension} not one of those supported: {', '.join(SUPPORTED_EXTENSIONS)}."
            )
        javafx = False
        bundle_type = self.env.get("bundle_type", DEFAULT_BUNDLE_TYPE)
        if bundle_type not in SUPPORTED_BUNDLE_TYPES:
            raise ProcessorError(
                f"bundle_type {bundle_type} not one of those supported: {', '.join(SUPPORTED_BUNDLE_TYPES)}."
            )
        if bundle_type.endswith("_fx"):
            bundle_type = bundle_type[:-3]
            javafx = True

        source_files = json.loads(self.download(api_url, text=True))
        for source_file in source_files:
            if (
                source_file["latest"]
                and source_file["os"] == "macos"
                and str(source_file["java_version"][0]) == java_major_version
                and source_file["arch"] == arch
                and source_file["ext"] == extension
                and source_file["bundle_type"] == bundle_type
                and source_file["javafx"] == javafx
            ):
                data = source_file
                break
        else:
            raise ProcessorError(
                f"No source file found matching the requested criteria of java_major_version={java_major_version}, arch={arch}, extension={extension}, bundle_type={bundle_type}, javafx={javafx}"
            )
        self.env["url"] = data["url"]
        self.env["version"] = ".".join([str(x) for x in data["zulu_version"]])
        self.env["java_version"] = ".".join([str(x) for x in data["java_version"]])
        self.env["openjdk_build_number"] = str(data["openjdk_build_number"])
        self.env["sha256_hash"] = data["sha256_hash"]
        self.env["munki_arch"] = MUNKI_ARCHS[arch]
        self.output(f"Found URL {self.env['url']} for version {self.env['version']}")


if __name__ == "__main__":
    PROCESSOR = AzulZuluJavaInfoProvider()
    PROCESSOR.execute_shell()
