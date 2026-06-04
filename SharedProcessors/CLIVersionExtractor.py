#!/usr/local/autopkg/python
"""CLIVersionExtractor - determine a CLI binary's version by executing it.

A backward-compatible superset of grahampugh's BinaryVersioner. It runs a binary
with a version parameter (e.g. ``--version``) and, optionally, applies a regular
expression with a single capture group to extract a clean version substring from
the output. Many CLIs print a product-name prefix alongside the version
(e.g. ``codex-cli 0.136.0``), which makes the raw output unsuitable for a package
name; ``version_regex`` lets the recipe pull just the version.

When ``version_regex`` is omitted the processor returns the whole stripped output,
matching BinaryVersioner's behaviour, so it can be used as a drop-in replacement.
Output is read from both stdout and stderr because some tools (e.g. wizcli) print
their version to stderr.
"""

import re
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["CLIVersionExtractor"]


class CLIVersionExtractor(Processor):
    """Run a CLI binary and extract its version, optionally via a regex."""

    description = __doc__

    input_variables = {
        "binary_path": {
            "required": True,
            "description": "Path to the binary to execute.",
        },
        "binary_parameter": {
            "required": False,
            "default": "--version",
            "description": (
                "Single argument passed to the binary to make it print its version, "
                "for example '--version' or 'version'. Defaults to '--version'."
            ),
        },
        "version_regex": {
            "required": False,
            "default": "",
            "description": (
                "Optional regular expression with exactly one capture group used to "
                "extract the version from the combined stdout/stderr output. If "
                "omitted, the whole stripped output is returned (BinaryVersioner "
                "behaviour)."
            ),
        },
    }

    output_variables = {
        "version": {
            "description": "Version extracted from the binary.",
        },
    }

    def main(self):
        binary_path = self.env["binary_path"]
        binary_parameter = self.env.get("binary_parameter") or "--version"
        version_regex = self.env.get("version_regex") or ""

        # Downloaded binaries are frequently not marked executable.
        try:
            subprocess.run(
                ["/bin/chmod", "+x", binary_path],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as err:
            raise ProcessorError(
                f"Could not make {binary_path} executable: "
                f"{err.stderr.decode(errors='replace').strip()}"
            )

        try:
            proc = subprocess.run(
                [binary_path, binary_parameter],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as err:
            raise ProcessorError(
                f"Failed to run '{binary_path} {binary_parameter}': "
                f"{(err.stderr or '').strip()}"
            )
        except OSError as err:
            raise ProcessorError(f"Could not execute {binary_path}: {err}")

        # Some CLIs print the version to stderr, others to stdout.
        output = (proc.stdout + proc.stderr).strip()
        if not output:
            raise ProcessorError(
                f"No output from '{binary_path} {binary_parameter}'; "
                "cannot determine version."
            )

        if version_regex:
            match = re.search(version_regex, output)
            if not match:
                raise ProcessorError(
                    f"version_regex {version_regex!r} did not match output: {output!r}"
                )
            if not match.groups():
                raise ProcessorError(
                    f"version_regex {version_regex!r} must contain a capture group."
                )
            version = match.group(1)
        else:
            version = output

        self.env["version"] = version
        self.output(f"Extracted version: {version}")


if __name__ == "__main__":
    PROCESSOR = CLIVersionExtractor()
    PROCESSOR.execute_shell()
