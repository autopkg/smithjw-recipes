#!/usr/local/autopkg/python
#
# Copyright 2025 James Smith
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
"""See docstring for TeradataProductURLFinder class"""

from __future__ import absolute_import

import json
import os
import re
import tempfile
from html.parser import HTMLParser
from urllib.parse import urlparse

from autopkglib import ProcessorError, URLGetter

__all__ = ["TeradataProductURLFinder"]


class TerradataVersionInfo(HTMLParser):
    def __init__(self):
        super().__init__()
        self.versions = []
        self.current_data = None

    def handle_starttag(self, tag, attrs):
        # Check for div tags with class "version" or "date"
        if tag == "div":
            for attr, value in attrs:
                if attr == "class" and value == "version":
                    self.current_data = "version"
                elif attr == "class" and value == "date":
                    self.current_data = "date"

    def handle_data(self, data):
        # Capture the version or date data
        if self.current_data == "version":
            self.versions.append({"version": data.strip()})
            self.current_data = None
        elif self.current_data == "date":
            if self.versions:
                self.versions[-1]["date"] = data.strip()
            self.current_data = None


class FilteredDownloadLinkExtractor(HTMLParser):
    def __init__(self, app_info, arch):
        super().__init__()
        self.app_info = app_info
        self.arch = arch
        self.filtered_link = None
        self.current_link = None
        self.current_text = ""
        self.capturing_text = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current_link = dict(attrs).get("href")
        elif tag == "span":
            self.capturing_text = True
            self.current_text = ""

    def handle_data(self, data):
        if self.capturing_text:
            self.current_text += (
                data.strip() if self.app_info.get("use_vantage_pattern") else data
            )

    def handle_endtag(self, tag):
        if tag == "span":
            self.capturing_text = False
        elif tag == "a" and self.current_link and self.current_text:
            if self._matches_criteria():
                self.filtered_link = self.current_link
            self._reset_state()

    def _matches_criteria(self):
        """Check if current link matches the filtering criteria."""
        # Search pattern matching (for TTU)
        if self.app_info.get("search_pattern"):
            return re.search(self.app_info["search_pattern"], self.current_text)

        # Vantage pattern matching
        if self.app_info.get("use_vantage_pattern"):
            text_lower = self.current_text.lower().replace(" ", "")
            if self.arch == "aarch64":
                return "macosm1pkg" in text_lower
            elif self.arch == "x86":
                return "macosintelpkg" in text_lower

        # Original Teradata pattern matching
        if "__" in self.current_text and "mac_" in self.current_text:
            product_name = self.current_text.split("__")[0]
            arch_part = self.current_text.split("mac_")[-1]
            return self.app_info.get("name") == product_name and self.arch in arch_part

        return False

    def _reset_state(self):
        """Reset parsing state."""
        self.current_link = None
        self.current_text = ""


class TeradataProductURLFinder(URLGetter):
    """Downloads Teradata Studio from Teradata's website."""

    description = __doc__

    # Teradata's site blocks curl's default UA; use a browser UA for all requests.
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.0 Safari/605.1.15"
    )
    input_variables = {
        "teradata_username": {
            "required": True,
            "description": ("Username Teradata Account"),
        },
        "teradata_password": {
            "required": True,
            "description": ("Password Teradata Account"),
        },
        "app": {
            "required": True,
            "description": (
                "App identifier (teradata_studio, teradata_studio_express, teradata_tools_utilities, teradata_vantage_editor)"
            ),
        },
        "architecture": {
            "required": False,
            "description": ("Architecture (aarch64 or x86)"),
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the requested Teradata product",
        },
        "version": {
            "description": "Version",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookie_file = None
        self.app_info = {
            "teradata_studio": {
                "nid": 183396,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/teradata-studio",
                "name": "TeradataStudio",
                "valid_archs": ["aarch64", "x86"],
            },
            "teradata_studio_express": {
                "nid": 7557,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/teradata-studio-express",
                "name": "TeradataStudioExpress",
                "valid_archs": ["aarch64", "x86"],
            },
            "teradata_tools_utilities": {
                "nid": 201214,
                "os": 1541,
                "url": "https://downloads.teradata.com/download/tools/teradata-tools-and-utilities-mac-osx-installation-package",
                "name": "TTU",
                "search_pattern": "^TTU\s\d+\.\d+\.\d+\.\d+\smacOS\sBase$",
            },
            "teradata_vantage_editor": {
                "nid": 202573,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/vantage-editor-desktop",
                "name": "Vantage Editor",
                "valid_archs": ["aarch64", "x86"],
                "use_vantage_pattern": True,
            },
        }

    def _get_cookie_file(self):
        """Get or create a temporary cookie file."""
        if not self.cookie_file:
            self.cookie_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=".txt"
            ).name
        return self.cookie_file

    def _cleanup_cookie_file(self):
        """Clean up the temporary cookie file."""
        if self.cookie_file and os.path.exists(self.cookie_file):
            os.unlink(self.cookie_file)
            self.cookie_file = None

    def _add_proxy_from_env(self, curl_cmd) -> None:
        """Append --proxy / --proxy-user to curl_cmd from proxy environment variables.

        All Teradata endpoints are HTTPS, so only HTTPS-specific and generic proxy
        vars are consulted — HTTP_PROXY/http_proxy are intentionally excluded to
        avoid the CGI header-injection vulnerability documented in curl's own source.

        Priority (mirrors curl for HTTPS targets):
          HTTPS_PROXY → https_proxy → ALL_PROXY → all_proxy

        If a proxy URL contains embedded credentials (http://user:pass@host:port)
        they are split out into a separate --proxy-user flag. The URL passed to
        --proxy is rebuilt without credentials so it is safe to log.

        Respects NO_PROXY/no_proxy: if the target host matches the bypass list the
        method is a no-op. Target hostname is resolved from the Teradata base URL
        since curl_cmd does not yet contain the destination at call time.

        If --proxy is already present in curl_cmd (set via curl_opts) this method
        is a no-op — explicit recipe/prefs configuration takes precedence.
        """
        # Explicit curl_opts proxy wins; do not override it.
        if "--proxy" in curl_cmd:
            return

        proxy_url = None
        for var in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
            proxy_url = os.environ.get(var)
            if proxy_url:
                break

        if not proxy_url:
            return

        # Respect NO_PROXY / no_proxy for the Teradata base domain.
        from urllib.request import proxy_bypass

        if proxy_bypass("downloads.teradata.com"):
            return

        parsed = urlparse(proxy_url)

        # Rebuild netloc without credentials; handle IPv6 literal hostnames
        # (urlparse strips brackets from hostname, so we must restore them).
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        netloc = f"{host}:{parsed.port}" if parsed.port else host
        clean_url = parsed._replace(netloc=netloc).geturl()

        curl_cmd.extend(["--proxy", clean_url])

        # Emit --proxy-user separately only when credentials are present.
        # The value is intentionally kept out of clean_url so that the URL
        # logged by download_with_curl does not contain the password.
        if parsed.username:
            curl_cmd.extend(
                ["--proxy-user", f"{parsed.username}:{parsed.password or ''}"]
            )

    def download_with_curl(self, curl_cmd, text=True) -> str:
        """Override to redact --proxy-user value from verbose curl command log."""
        safe_cmd = []
        skip_next = False
        for arg in curl_cmd:
            if skip_next:
                safe_cmd.append("<redacted>")
                skip_next = False
            else:
                safe_cmd.append(arg)
                if arg in ("--proxy-user", "-U"):
                    skip_next = True
        self.output(f"Curl command: {safe_cmd}", verbose_level=4)
        proc_stdout, proc_stderr, retcode = self.execute_curl(curl_cmd, text)
        if retcode:
            curl_err = self.parse_curl_error(proc_stderr)
            raise ProcessorError(f"curl failure: {curl_err} (exit code {retcode})")
        return proc_stdout

    def _build_post_curl_cmd(
        self, url, data, use_cookies=True, save_cookies=False, include_headers=False
    ):
        """Build a POST curl command with common options."""
        curl_cmd = self.prepare_curl_cmd()
        self._add_proxy_from_env(curl_cmd)
        self.add_curl_common_opts(curl_cmd)
        curl_cmd.extend(["--user-agent", self.USER_AGENT])
        curl_cmd.extend(["-X", "POST"])
        curl_cmd.extend(["-H", "Content-Type: application/x-www-form-urlencoded"])

        if save_cookies:
            curl_cmd.extend(["-c", self._get_cookie_file()])
        elif use_cookies:
            curl_cmd.extend(["-b", self._get_cookie_file()])

        if include_headers:
            curl_cmd.extend(["-D", "-"])

        for key, value in data.items():
            curl_cmd.extend(["-d", f"{key}={value}"])
        curl_cmd.append(url)
        return curl_cmd

    def _build_get_curl_cmd(self, url, use_cookies=True):
        """Build a GET curl command with common options."""
        curl_cmd = self.prepare_curl_cmd()
        self._add_proxy_from_env(curl_cmd)
        self.add_curl_common_opts(curl_cmd)
        curl_cmd.extend(["--user-agent", self.USER_AGENT])
        if use_cookies:
            curl_cmd.extend(["-b", self._get_cookie_file()])
        curl_cmd.append(url)
        return curl_cmd

    def download(self, url, headers=None, text=False) -> str:
        """Override URLGetter.download to ensure proxy env vars are applied."""
        curl_cmd = self.prepare_curl_cmd()
        self._add_proxy_from_env(curl_cmd)
        self.add_curl_common_opts(curl_cmd)
        curl_cmd.extend(["--user-agent", self.USER_AGENT])
        self.add_curl_headers(curl_cmd, headers)
        curl_cmd.append(url)
        return self.download_with_curl(curl_cmd, text)

    def _validate_cloudfront_url(self, url, app):
        """Validate CloudFront URL for Vantage apps."""
        if self.app_info[app].get("use_vantage_pattern", False):
            if ".cloudfront.net" not in url:
                raise ProcessorError("Unexpected download URL. Not a CloudFront link.")

    def get_product_version(self, app):
        """Returns the product version using multiple detection strategies."""
        url = self.app_info[app]["url"]
        downloads_page = self.download(url, text=True)

        # Strategy 1: Single version div (Vantage pattern)
        match = re.search(r'<div id="single_version">([^<]+)</div>', downloads_page)
        if match:
            version = match.group(1).strip()
            self.output(f"Found version (single_version): {version}")
            return version

        # Strategy 2: Select option pattern (Vantage fallback)
        match = re.search(
            r'<select[^>]*id="edit-version"[^>]*>.*?<option value="([^"]+)"',
            downloads_page,
            re.DOTALL,
        )
        if match:
            version = match.group(1).strip()
            self.output(f"Found version (select_option): {version}")
            return version

        # Strategy 3: HTML parser for version/date divs (Original Teradata)
        parser = TerradataVersionInfo()
        parser.feed(downloads_page)
        if parser.versions:
            version = parser.versions[0]["version"]
            self.output(f"Found version (html_parser): {version}")
            return version

        # Strategy 4: Generic version pattern matching
        version_patterns = [
            r'version["\s]*:?\s*["\']([^"\']+)["\']',
            r'<span[^>]*class="version"[^>]*>([^<]+)</span>',
            r'data-version="([^"]+)"',
        ]

        for pattern in version_patterns:
            match = re.search(pattern, downloads_page, re.IGNORECASE)
            if match:
                version = match.group(1).strip()
                self.output(f"Found version (pattern_match): {version}")
                return version

        # Default fallback
        default_version = (
            "1.0" if self.app_info[app].get("use_vantage_pattern") else None
        )
        self.output(f"Version not found, using default: {default_version}")
        return default_version

    def get_download_url(self, username, password, app, architecture):
        try:
            # Step 1: Login
            login_url = "https://downloads.teradata.com/user/login?destination="
            login_data = {
                "name": username,
                "pass": password,
                "form_id": "user_login_form",
            }
            curl_cmd = self._build_post_curl_cmd(
                login_url, login_data, use_cookies=False, save_cookies=True
            )
            self.download_with_curl(curl_cmd, text=True)

            # Step 2: Get downloads packages filter
            filter_data = {
                "os": self.app_info[app]["os"],
                "version": self.env["version"],
                "nid": self.app_info[app]["nid"],
                "check_full_user_req": 0,
                "check_user_details": "false",
            }
            curl_cmd = self._build_post_curl_cmd(
                "https://downloads.teradata.com/downloads-packages/filter", filter_data
            )
            response_content = self.download_with_curl(curl_cmd, text=True)
            download_data = json.loads(response_content)

            # Step 3: Parse download links
            parser = FilteredDownloadLinkExtractor(self.app_info[app], architecture)
            parser.feed(download_data[0]["downloads_html"])
            product_link = parser.filtered_link
            if not product_link:
                raise ProcessorError(
                    f"Download link not found for {self.app_info[app]['name']}. Please check your credentials or the product name."
                )

            # Step 4: Prepare license acceptance data
            if self.app_info[app].get("use_vantage_pattern", False):
                # Vantage pattern: Get form tokens
                curl_cmd = self._build_get_curl_cmd(product_link)
                form_page_content = self.download_with_curl(curl_cmd, text=True)

                form_build_id = re.search(
                    r'name="form_build_id" value="([^"]+)"', form_page_content
                )
                form_token = re.search(
                    r'name="form_token" value="([^"]+)"', form_page_content
                )

                if not form_build_id or not form_token:
                    raise ProcessorError("Unable to parse license form tokens.")

                final_data = {
                    "op": "I Agree",
                    "form_id": "license_popup_form",
                    "form_build_id": form_build_id.group(1),
                    "form_token": form_token.group(1),
                }
            else:
                # Original Teradata pattern
                final_data = {
                    "downloadnid": self.app_info[app]["nid"],
                    "form_id": "license_popup_form",
                }

            # Step 5: Submit license acceptance and get download URL
            curl_cmd = self._build_post_curl_cmd(
                product_link, final_data, use_cookies=False, include_headers=True
            )

            try:
                response_with_headers = self.download_with_curl(curl_cmd, text=True)
                # Parse headers from successful response
                headers = self.parse_headers(response_with_headers.split("\r\n\r\n")[0])
                download_url = headers.get("location") or headers.get("http_redirected")
            except ProcessorError as e:
                # Handle redirect responses (common for download URLs)
                if any(code in str(e) for code in ["301", "302", "303"]):
                    location_match = re.search(r"Location:\s*([^\r\n]+)", str(e))
                    if location_match:
                        download_url = location_match.group(1).strip()
                    else:
                        raise ProcessorError(
                            "Could not extract download URL from redirect response"
                        )
                else:
                    raise e

            if not download_url:
                raise ProcessorError(
                    "Could not extract download URL from response headers"
                )

            # Validate URL for specific app types
            self._validate_cloudfront_url(download_url, app)

            self.output(f"Selected download link: {download_url}")
            return download_url

        finally:
            # Always cleanup cookie file
            self._cleanup_cookie_file()

    def main(self):
        # Validate required parameters
        username = self.env.get("teradata_username")
        password = self.env.get("teradata_password")
        app = self.env.get("app")

        if not username or not password:
            raise ProcessorError("Username and password are required.")

        if not app:
            raise ProcessorError("App parameter is required.")

        if app not in self.app_info:
            raise ProcessorError(
                f"Invalid app name: {app}. Valid options are: {list(self.app_info.keys())}"
            )

        # Handle architecture parameter
        architecture = self.env.get("architecture")
        valid_archs = self.app_info[app].get("valid_archs")

        if valid_archs:
            if not architecture:
                # Default to first valid architecture if not specified
                architecture = valid_archs[0]
                self.output(
                    f"Architecture not specified, defaulting to: {architecture}"
                )
            elif architecture not in valid_archs:
                raise ProcessorError(
                    f"Invalid architecture: {architecture}. Valid options are: {valid_archs}"
                )

        try:
            # Get product version and download URL
            self.env["version"] = self.get_product_version(app)
            self.env["url"] = self.get_download_url(
                username, password, app, architecture
            )

            self.output(
                f"Successfully found download for {self.app_info[app].get('name', app)}"
            )
            self.output(f"Version: {self.env['version']}")
            self.output(f"URL: {self.env['url']}")

        except Exception as e:
            self.output(f"Error processing {app}: {str(e)}")
            raise ProcessorError(f"Failed to get download URL for {app}: {str(e)}")


if __name__ == "__main__":
    PROCESSOR = TeradataProductURLFinder()
    PROCESSOR.execute_shell()
