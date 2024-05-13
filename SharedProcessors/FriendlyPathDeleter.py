#!/usr/local/autopkg/python
#
# Copyright 2013 Greg Neagle
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
"""See docstring for FriendlyPathDeleter class"""

import os
import shutil
import time

from autopkglib import Processor, ProcessorError

__all__ = ["FriendlyPathDeleter"]


class FriendlyPathDeleter(Processor):
    """Deletes file paths."""

    input_variables = {
        "path_list": {
            "required": True,
            "description": (
                "An array or list of pathnames to be deleted, "
                "even if that list contains a single item."
            ),
        },
        "fail_deleter_silently": {
            "required": False,
            "description": (
                "If this is set to True, FriendlyPathDeleter "
                "will not error out when it can't find a given path to remove. "
                "False by default"
            ),
        },
    }
    output_variables = {}
    description = __doc__

    def main(self):
        # if recipe writer gave us a single string instead of a list of strings,
        # convert it to a list of strings
        if isinstance(self.env["path_list"], str):
            self.env["path_list"] = [self.env["path_list"]]

        fail_deleter_silently = self.env.get("fail_deleter_silently", False)

        for path in self.env["path_list"]:
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    self.output(f"Deleted {path}")
                elif os.path.isdir(path):
                    dt = 1
                    for _i in range(5):
                        try:
                            shutil.rmtree(path)
                            self.output(f"Deleted {path}")
                            return
                        except OSError:
                            self.output(f"Unable to remove path: {path}")
                            self.output(f"Retrying in {dt} seconds")
                            time.sleep(dt)
                            dt *= 2
                    shutil.rmtree(path, ignore_errors=fail_deleter_silently)
                    self.output(f"Deleted {path}")
                elif not os.path.exists(path):
                    if not fail_deleter_silently:
                        raise ProcessorError(
                            f"Could not remove {path} - it does not exist! "
                            "You can set '--key fail_deleter_silently=True' to bypass "
                            "this error."
                        )
                    else:
                        self.output(f"Path does not exist, skipping: {path}")
                else:
                    raise ProcessorError(
                        f"Could not remove {path} - it is not a file, link, "
                        "or directory"
                    )
            except OSError as err:
                raise ProcessorError(f"Could not remove {path}: {err}") from err


if __name__ == "__main__":
    PROCESSOR = FriendlyPathDeleter()
    PROCESSOR.execute_shell()
