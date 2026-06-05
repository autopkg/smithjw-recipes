#!/usr/local/autopkg/python
"""
WizVersionExtractor - Extracts version from Wiz CLI binary
"""

import subprocess
import re
from autopkglib import Processor, ProcessorError

__all__ = ["WizVersionExtractor"]

class WizVersionExtractor(Processor):
    """Extracts version from Wiz CLI binary by executing it."""

    description = __doc__

    input_variables = {
        "input_path": {
            "required": True,
            "description": "Path to the Wiz CLI binary to extract version from.",
        },
    }

    output_variables = {
        "version": {
            "description": "Version extracted from the Wiz CLI binary.",
        },
    }

    def main(self):
        binary_path = self.env["input_path"]

        try:
            # Make binary executable
            subprocess.run(['/bin/chmod', '+x', binary_path], check=True, capture_output=True)

            # Execute wizcli version
            result = subprocess.run(
                [binary_path, 'version'],
                capture_output=True,
                text=True,
                check=True
            )

            # Wiz CLI outputs version to stderr, not stdout
            output = result.stdout + result.stderr

            # Extract version from output
            # Expected format: "Wiz CLI vX.Y.Z" or just "vX.Y.Z"
            version_match = re.search(r'v?([0-9]+\.[0-9]+\.[0-9]+)', output)

            if version_match:
                version = version_match.group(1)
                self.env["version"] = version
                self.output(f"Extracted version: {version}")
            else:
                raise ProcessorError(f"Could not extract version from output. stdout: {result.stdout}, stderr: {result.stderr}")

        except subprocess.CalledProcessError as e:
            raise ProcessorError(f"Failed to execute binary: {e.stderr}")
        except Exception as e:
            raise ProcessorError(f"Error extracting version: {str(e)}")

if __name__ == "__main__":
    PROCESSOR = WizVersionExtractor()
    PROCESSOR.execute_shell()
