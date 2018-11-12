# The MIT License (MIT)
#
# Copyright (c) 2018 Michael Schroeder
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import datetime
import sys
import argparse
import traceback

import requests

from adabot import github_requests as github
from adabot import pypi_requests as pypi
from adabot import circuitpython_libraries as cpy_libs

# Setup ArgumentParser
cmd_line_parser = argparse.ArgumentParser(description="Adabot utility for CircuitPython Library download stats." \
                                          " Provides stats for the Adafruit CircuitPython Bundle, and PyPi if available.",
                                          prog="Adabot CircuitPython Libraries Download Stats")
cmd_line_parser.add_argument("-o", "--output_file", help="Output log to the filename provided.",
                             metavar="<OUTPUT FILENAME>", dest="output_file")
cmd_line_parser.add_argument("-v", "--verbose", help="Set the level of verbosity printed to the command prompt."
                             " Zero is off; One is on (default).", type=int, default=1, dest="verbose", choices=[0,1])

# Global variables
output_filename = None
verbosity = 1
file_data = []

def get_pypi_stats(repo):
    api_url = "https://pypistats.org/api/packages/" + repo.replace("_", "-").lower() + "/recent"
    pypi_stats = requests.get(api_url, timeout=10)
    if not pypi_stats.ok:
        return "Failed to retrieve data ({})".format(pypi_stats.text)

    return pypi_stats.json()["data"]["last_week"]

def get_bundle_stats(bundle):
    """ Returns the download stats for 'bundle'. Uses release tag names to compile download
        stats for the last 7 days. This assumes an Adabot release within that time frame, and
        that tag name(s) will be the date (YYYYMMDD).
    """
    stats_dict = {}
    bundle_stats = github.get("/repos/adafruit/" + bundle + "/releases")
    if not bundle_stats.ok:
        return {"Failed to retrieve bundle stats": bundle_stats.text}
    start_date = datetime.date.today()

    for release in bundle_stats.json():
        try:
            release_date = datetime.date(int(release["tag_name"][:4]),
                                         int(release["tag_name"][4:6]),
                                         int(release["tag_name"][6:]))
        except:
            output_handler("Skipping release. Tag name invalid: {}".format(release["tag_name"]))
            continue
        if (start_date - release_date).days > 7:
            break

        for asset in release["assets"]:
            if asset["name"].startswith("adafruit"):
                asset_name = asset["name"][:asset["name"].rfind("-")]
                if asset_name in stats_dict:
                    stats_dict[asset_name] = stats_dict[asset_name] + asset["download_count"]
                else:
                    stats_dict[asset_name] = asset["download_count"]

    return stats_dict

def output_handler(message="", quiet=False):
    """Handles message output to prompt/file for functions."""
    if output_filename is not None:
        file_data.append(message)
    if verbosity and not quiet:
        print(message)

def run_stat_check():
    output_handler("Adafruit CircuitPython Library Download Stats")
    output_handler("Report Date: {}".format(datetime.datetime.now().strftime("%d %B %Y, %I:%M%p")))
    output_handler()
    output_handler("Adafruit_CircuitPython_Bundle downloads for the past week:")
    for stat in get_bundle_stats("Adafruit_CircuitPython_Bundle").items():
        output_handler(" * {0}: {1}".format(stat[0], stat[1]))
    output_handler()

    pypi_downloads = {}
    output_handler("Adafruit CircuitPython Library PyPi downloads for the past week: ")
    repos = cpy_libs.list_repos()
    for repo in repos:
        if repo["owner"] == "adafruit" and repo["name"].startswith("Adafruit_CircuitPython"):
            if cpy_libs.repo_is_on_pypi(repo):
                pypi_downloads[repo["name"]] = get_pypi_stats(repo["name"])
    for stat in sorted(pypi_downloads.items()):
        output_handler(" * {0}: {1}".format(stat[0], stat[1]))

if __name__ == "__main__":
    cmd_line_args = cmd_line_parser.parse_args()
    verbosity = cmd_line_args.verbose
    if cmd_line_args.output_file:
        output_filename = cmd_line_args.output_file
    try:
        run_stat_check()
    except:
        if output_filename is not None:
            exc_type, exc_val, exc_tb = sys.exc_info()
            output_handler("Exception Occurred!", quiet=True)
            output_handler(("-"*60), quiet=True)
            output_handler("Traceback (most recent call last):", quiet=True)
            tb = traceback.format_tb(exc_tb)
            for line in tb:
                output_handler(line, quiet=True)
            output_handler(exc_val, quiet=True)

        raise

    finally:
        if output_filename is not None:
            with open(output_filename, 'w') as f:
                for line in file_data:
                    f.write(str(line) + "\n")
