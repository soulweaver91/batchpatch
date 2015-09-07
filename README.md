BatchPatch
==========

BatchPatch is a Python script designed for automating the generation and distribution of a batch of patch files with
the [xdelta](https://github.com/jmacd/xdelta) tool. The targeted use case is anime batch releases in particular; the
script expects names like `[group] Series name - 01v3 (720p) [1357acde].mkv`, and corresponding file pairs are
identified by that version marker. In addition to the patch files, the script also writes a ready-to-use batch file
for Windows with which the recipient can easily apply all of the patches to their files.

## Requirements

*   [Python 3](https://www.python.org/downloads/). More recent is probably better, written and tested on Python 3.4.3.
*   [pip](https://pip.pypa.io/en/latest/installing.html), if it didn't come bundled with your version of Python 3.
*   An [xdelta](https://github.com/jmacd/xdelta) executable, copied into the same folder as the script.
    Dealing with different versions and xdelta's license requiring a full copy of source code distributed even with
    only the executable itself is not ideal, so you'll have to do this manually.

## Installing
After cloning the repository, install dependencies:

```pip install -r requirements.txt```

That's it.

## Usage
```python batchpatch.py -o "olddir" -n "newdir" -t "patchdir" -l loglevel```

*   `olddir` and `newdir` must both be existing directories. For each detected file representing a certain content,
    the highest version in each folder is compared and patched. These both are required for obvious reasons.
*   `patchdir` doesn't have to exist prior to running the script. If not set, the patches will be created under a
    time based automatic folder under the working directory.
*   `loglevel` controls the amount of output the script will print. Valid values are, in order of verbosity:
    * `debug` (prints everything)
    * `notice` (default if not set)
    * `warning`
    * `error`
    * `silent` (doesn't print anything)
    
Additionally, switches `-v` and `-h` for version info and help are supported.

## What constitutes a suitable pair of files for a patch?
The internal regular expression splits each filename it comes across into a few distinct pieces in this order:

*   Group short name in square brackets, if present.
*   Main name.
*   Episode number (also allowing alphabets, i.e. "S1" or "NCOP2" are valid episode numbers), if present. A leading dash
    surrounded by spaces is expected before the number.
*   Version tag in the form "vX", if present. Absence implies version one.
*   Additional qualifiers in parentheses, if present. Commonly contains data like the resolution.
*   CRC hash in square brackets, if present.
*   The file extension.

The files are considered to be compatible for patching if their group name, main name, episode number, qualifiers and
file extension match and additionally their versions differ. Take note that missing values also match. As most elements
are optional, the minimal case of compatible files is as simple as `file.txt` and `file v2.txt`.

The regular expression cannot currently be configured without editing the script.

## License
The source code is licensed under the [MIT license](http://opensource.org/licenses/MIT).
