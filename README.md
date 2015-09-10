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

## Basic usage
```python batchpatch.py -o "olddir" -n "newdir"```

This will create patches for each matching pair of files between the folders `olddir` and `newdir` into a new 
timestamped directory in the same folder as the script itself.

## Switch reference
*   `-o dir`, `--olddir dir`: Specifies the directory with the old files.
*   `-n dir`, `--newdir dir`: Specifies the directory with the new files.
*   `-t dir`, `--target dir`: Specifies where the patch files and the script should be written to. It will be created
    if it does not yet exist.
*   `-l level`, `--loglevel level`: Controls the amount of output the script will print.
    Valid values are, in order of verbosity:
    * `debug` (prints everything)
    * `notice` (default if not set)
    * `warning`
    * `error`
    * `silent` (doesn't print anything)
*   `-x path`, `--xdelta_path path`: defines an alternate location for the xdelta executable. By default, one is
    expected to be located in the same folder as the script.
*   `-v`, `--version`: Prints the version information and exits.
*   `-h`, `--help`: Prints a help message, which contains more or less the same information as this section.
*   `--script-lang lang`: Selects another language to use when writing the automatic patch applying script.
    Allowed values are defined by the present subfolders in the `i18n` directory.
*   `--script-name name`: Specifies the filename to use for the patch script, without the file extension.
    Default name is 'apply'.

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
