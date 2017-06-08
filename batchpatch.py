#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'Soulweaver'

import argparse
import os
import re
import time
import shutil
import colorama
import subprocess
import unicodedata
import gettext
from zipfile import ZipFile
from datetime import datetime
from dateutil import tz
from logger import LogLevel, Logger


class BatchPatch:
    PROG_NAME = 'BatchPatch'
    PROG_VERSION = '0.3'
    PROG_URL = 'https://github.com/soulweaver91/batchpatch'
    LOCALE_CATALOG = 'batchpatch'

    logger = None
    script_options = {
        'script_lang': 'en_US',
        'script_name': 'apply'
    }
    patch_options = {
        'filename_pattern': None
    }
    archive_options = {
        'create_zip': False,
        'zip_name': 'patch'
    }

    log_level = LogLevel.notice
    xdelta_location = ''
    locale_dir = ''

    def __init__(self):
        colorama.init()

        self.xdelta_location = os.path.join(BatchPatch.get_install_path(), 'xdelta3.exe')
        self.locale_dir = os.path.join(BatchPatch.get_install_path(), 'i18n')

    def print_welcome(self):
        # Print this even on the highest levels, but not on silent, and without the log prefix
        if self.log_level != LogLevel.silent:
            print('{} version {}'.format(self.PROG_NAME, self.PROG_VERSION))

    def get_version(self):
        return self.PROG_VERSION

    def get_name(self):
        return self.PROG_NAME

    def switch_languages(self, lang):
        try:
            gettext.translation('batchpatch', self.locale_dir, languages=[lang, 'en_US']).install()
        except OSError as e:
            self.logger.log('Selecting language {} failed: {}'.format(lang, e.strerror), LogLevel.error)

    def run(self):
        parser = argparse.ArgumentParser(
            description="Generates distribution ready patches for anime batch releases."
        )
        parser.add_argument(
            '-o', '--old',
            action='store',
            help='The path to the folder with the old files. Required.',
            required=True,
            metavar='directory'
        )
        parser.add_argument(
            '-n', '--new',
            action='store',
            help='The path to the folder with the new files. Required.',
            required=True,
            metavar='directory'
        )
        parser.add_argument(
            '-t', '--target',
            action='store',
            help='The path where the output should be written to. If not specified, '
                 'a new date stamped subfolder will be written under the current '
                 'working directory.',
            default=self.get_default_output_folder(),
            metavar='directory'
        )
        parser.add_argument(
            '-l', '--loglevel',
            action='store',
            help='The desired verbosity level. Any messages with the same or higher '
                 'level than the chosen one will be displayed. '
                 'Available values: debug (most verbose), notice, warning, error, silent '
                 '(least verbose, does not print anything). Default: notice.',
            choices=[e.name for e in LogLevel],
            default='notice',
            metavar='level'
        )
        parser.add_argument(
            '-x', '--xdelta',
            action='store',
            help='An alternative location for the xdelta3 executable to search instead of '
                 'the same directory as the script.',
            default=self.xdelta_location,
            metavar='path'
        )
        parser.add_argument(
            '-z', '--zip',
            action='store_true',
            help='Create a ZIP file out of the created patch files.',
            default=self.xdelta_location
        )
        parser.add_argument(
            '--zip-name',
            action='store',
            help='The filename to save the ZIP with. Only meaningful if -z was set.',
            default='patch.zip',
            metavar='path'
        )
        parser.add_argument(
            '--script-lang',
            action='store',
            help='The language to use in the generated script.',
            default='en_US',
            choices=[d for d in os.listdir(self.locale_dir) if os.path.isdir(os.path.join(self.locale_dir, d))],
            metavar='lang_code'
        )
        parser.add_argument(
            '--script-name',
            action='store',
            help='The filename to use for the generated script, without the extension. \'apply\' by default.',
            default='apply',
            metavar='name'
        )
        parser.add_argument(
            '--patch-pattern',
            action='store',
            help='The filename to use for the patch files. Consult README.md for available variables.',
            default='{name}{specifier_items[0]}_{ep}_v{v_old}v{v_new}.vcdiff',
            metavar='name'
        )
        parser.add_argument(
            '-v', '--version',
            action='version',
            version="{} version {}".format(self.PROG_NAME, self.PROG_VERSION)
        )

        args = parser.parse_args()
        self.log_level = LogLevel[args.loglevel]
        self.logger = Logger(self.log_level)
        self.script_options['script_lang'] = args.script_lang
        self.script_options['script_name'] = args.script_name
        self.patch_options['filename_pattern'] = args.patch_pattern
        self.archive_options['zip_name'] = args.zip_name

        if args.xdelta is not None:
            self.xdelta_location = args.xdelta
            self.logger.log('Custom xdelta location \'{}\' read from the command line.'.format(args.xdelta),
                            LogLevel.debug)

        self.print_welcome()
        self.check_prerequisites(args)
        file_pairs = self.identify_file_pairs_by_name(args.old, args.new)

        if len(file_pairs) > 0:
            # Sort in alphabetical order for nicer output all around
            file_pairs.sort(key=lambda item: item[0])

            self.generate_patches(file_pairs, args.target)
            self.generate_win_script(file_pairs, args.target)
            self.copy_executable(args.target)

            if args.zip is not None:
                self.create_archive(file_pairs, args.target)

            self.logger.log('Done.', LogLevel.notice)
        else:
            self.logger.log('No files to generate patches for.', LogLevel.notice)

    def check_prerequisites(self, args):
        self.logger.log('Checking prerequisites.', LogLevel.debug)
        for p in ('old', 'new', 'target'):
            self.logger.log('Verifying existence of {} directory.'.format(p), LogLevel.debug)
            try:
                path = getattr(args, p)
            except AttributeError:
                self.logger.log('Expected parameter \'{}\' was missing!'.format(p), LogLevel.error)
                exit()

            if not os.path.isdir(path):
                if p != 'target':
                    self.logger.log('{} is not a valid path!'.format(path), LogLevel.error)
                    exit()
                else:
                    if os.path.exists(path):
                        self.logger.log('\'{}\' exists and is not a directory!'.format(path), LogLevel.error)
                        exit()
                    else:
                        self.logger.log('Creating output directory \'{}\'.'.format(path), LogLevel.notice)
                        try:
                            os.makedirs(path)
                        except OSError as e:
                            self.logger.log('Error while creating directory \'{]\': {}'.format(path, e.strerror),
                                            LogLevel.error)
                            exit()
            else:
                self.logger.log('\'{}\' was found.'.format(path), LogLevel.debug)

        self.logger.log('Verifying a xdelta executable is found from the specified location.', LogLevel.debug)

        if not os.path.exists(self.xdelta_location) or not os.path.isfile(self.xdelta_location):
            self.logger.log('The xdelta3 executable could not be found at \'{}\'!'.format(self.xdelta_location),
                            LogLevel.error)
            self.logger.log('Please download correct version for your system from the xdelta site or', LogLevel.error)
            self.logger.log('compile it yourself, and then add it to the same directory as this script', LogLevel.error)
            self.logger.log('under the name xdelta3.exe.', LogLevel.error)
            exit()

        if not os.access(self.xdelta_location, os.X_OK):
            self.logger.log('The xdelta3 executable at \'{}\' doesn\'t have execution permissions!'.format(
                self.xdelta_location), LogLevel.error
            )
            exit()

        self.logger.log('Prerequisites OK.', LogLevel.debug)

    def generate_patches(self, file_pairs, target_dir):
        self.logger.log('Generating patches for {} file pairs.'.format(str(len(file_pairs))), LogLevel.debug)
        for pair in file_pairs:
            self.logger.log('Creating patch: {} -> {}'.format(pair[0], pair[1]), LogLevel.notice)

            effective_source = pair[0]
            effective_target = pair[1]
            temp_source_name = None
            temp_target_name = None
            if not pair[4]:
                temp_source_name = '~' + os.path.basename(pair[2]) + '.src'
                temp_target_name = '~' + os.path.basename(pair[2]) + '.dst'
                self.logger.log(('Filename is not safe for xdelta on Windows. Copying files to temporary '
                                'names {} and {}.').format(temp_source_name, temp_target_name), LogLevel.notice)
                shutil.copyfile(pair[0], temp_source_name)
                shutil.copyfile(pair[1], temp_target_name)
                effective_source = temp_source_name
                effective_target = temp_target_name

            cmd = [
                self.xdelta_location,
                '-e',        # Create patch
                '-9',        # Use maximum compression
                '-s',        # Read from file
                effective_source,     # Old file
                effective_target,     # New file
                os.path.join(target_dir, pair[2])    # Patch destination
            ]

            if self.log_level.numval <= LogLevel.notice.numval:
                # Pass verbose flag to xdelta if using a relatively verbose logging level
                cmd.insert(2, '-v')
            elif self.log_level.numval == LogLevel.silent.numval:
                # Pass quiet flag if using the silent logging level
                cmd.insert(2, '-q')

            try:
                self.logger.log('Starting subprocess, command line: {}'.format(" ".join(cmd)), LogLevel.debug)
                ret = subprocess.call(cmd)
                if ret != 0:
                    self.logger.log('xdelta returned a non-zero return value {}! '
                                    'This probably means something went wrong.'.format(str(ret)), LogLevel.warning)

                if not pair[4]:
                    self.logger.log('Removing temporary files.'.format(temp_source_name, temp_target_name),
                                    LogLevel.notice)
                    os.unlink(temp_source_name)
                    os.unlink(temp_target_name)

            except (OSError, IOError) as e:
                self.logger.log('Starting the subprocess failed! ' + e.strerror, LogLevel.warning)

    def generate_win_script(self, file_pairs, target_dir):
        self.switch_languages(self.script_options['script_lang'])

        fh = open(os.path.join(target_dir, self.script_options['script_name'] + '.cmd'),
                  mode='w', newline='\r\n', encoding='utf-8')
        self.logger.log('Generating Windows update script.'.format(str(len(file_pairs))), LogLevel.debug)
        fh.write('@echo off\n\n')
        fh.write('REM Generated by {} version {}\n'.format(self.PROG_NAME, self.PROG_VERSION))
        fh.write('REM on {}\n'.format(datetime.now(tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S %z (%Z)")))
        fh.write('REM {}\n\n'.format(self.PROG_URL))
        fh.write('setlocal\n')
        fh.write('for /f "tokens=2 delims=:." %%x in (\'chcp\') do set cp=%%x\n')
        fh.write('chcp 65001 > NUL\n')
        fh.write('set pnum=0\n')
        fh.write('set nnum=0\n')
        fh.write('set fnum=0\n\n')

        fh.write('IF NOT EXIST "{}" (\n'.format(os.path.basename(self.xdelta_location)))
        fh.write('  echo {msg}\n'.format(
            msg=_('The xdelta executable was not found! It is required for this script to work!'))
        )
        fh.write('  pause\n')
        fh.write('  exit /b 1\n')
        fh.write(')\n\n')

        for pair in file_pairs:
            if pair[4]:
                fh.write(
                    (
                        'IF EXIST "{old}" (\n' +
                        '  IF NOT EXIST "{new}" (\n' +
                        '    echo {msg}\n'.format(msg=_('Patching {old_esc}...')) +
                        '    set /a pnum+=1\n' +
                        '    "{xdelta}" -d -v -s "{old}" "{patch}" "{new}" || (\n' +
                        '      echo {msg}\n'.format(msg=_('Patching {old_esc} failed!')) +
                        '      set /a pnum-=1\n' +
                        '      set /a fnum+=1\n' +
                        '    )\n' +
                        '  ) ELSE (\n' +
                        '    echo {msg}\n'.format(msg=_('{new_esc} already exists, skipping...')) +
                        '    set /a nnum+=1\n' +
                        '  )\n' +
                        ') ELSE (\n' +
                        '  echo {msg}\n'.format(msg=_('{old_esc} not present in folder, skipping...')) +
                        '  set /a nnum+=1\n' +
                        ')\n'
                    ).format(
                        old=os.path.basename(pair[0]),
                        new=os.path.basename(pair[1]),
                        patch=os.path.basename(pair[2]),
                        old_esc=self.cmd_escape(os.path.basename(pair[0])),
                        new_esc=self.cmd_escape(os.path.basename(pair[1])),
                        xdelta=os.path.basename(self.xdelta_location)
                    )
                )
            else:
                fh.write(
                    (
                        'IF EXIST "{old}" (\n' +
                        '  IF NOT EXIST "{new}" (\n' +
                        '    echo {msg}\n'.format(msg=_('Patching {old_esc}...')) +
                        '    set /a pnum+=1\n' +
                        '    REM xdelta unicode incompatibility workaround\n' +
                        '    copy "{old}" "{intermediate_old}" > NUL\n' +
                        '    "{xdelta}" -d -v -s "{intermediate_old}" "{patch}" "{intermediate_new}" || (\n' +
                        '      echo {msg}\n'.format(msg=_('Patching {old_esc} failed!')) +
                        '      set /a pnum-=1\n' +
                        '      set /a fnum+=1\n' +
                        '    )\n' +
                        '    REM xdelta unicode incompatibility workaround\n' +
                        '    move "{intermediate_new}" "{new}" > NUL\n' +
                        '    del "{intermediate_old}" > NUL\n' +
                        '  ) ELSE (\n' +
                        '    echo {msg}\n'.format(msg=_('{new_esc} already exists, skipping...')) +
                        '    set /a nnum+=1\n' +
                        '  )\n' +
                        ') ELSE (\n' +
                        '  echo {msg}\n'.format(msg=_('{old_esc} not present in folder, skipping...')) +
                        '  set /a nnum+=1\n' +
                        ')\n'
                    ).format(
                        old=os.path.basename(pair[0]),
                        new=os.path.basename(pair[1]),
                        intermediate_old=('~' + os.path.basename(pair[2]) + '.src'),
                        intermediate_new=('~' + os.path.basename(pair[2]) + '.dst'),
                        patch=os.path.basename(pair[2]),
                        old_esc=self.cmd_escape(os.path.basename(pair[0])),
                        new_esc=self.cmd_escape(os.path.basename(pair[1])),
                        xdelta=os.path.basename(self.xdelta_location)
                    )
                )

        fh.write('echo {msg}\n'.format(msg=_('Finished, with %pnum% files patched, %nnum% skipped and %fnum% failed.')))
        fh.write('pause\n')
        fh.write('chcp %cp% > NUL\n')
        fh.close()

        self.switch_languages('en_US')

    def copy_executable(self, target_dir):
        self.logger.log('Copying xdelta to the target folder {}.'.format(target_dir), LogLevel.debug)
        shutil.copy(os.path.join(os.getcwd(), self.xdelta_location),
                    os.path.join(target_dir, os.path.basename(self.xdelta_location)))

    def create_archive(self, file_pairs, target_dir):
        zip_path = os.path.join(target_dir, self.archive_options['zip_name'])
        self.logger.log('Creating a ZIP archive of the patch to \'{}\'.'.format(zip_path), LogLevel.debug)
        zip = ZipFile(zip_path, 'w')

        for pair in file_pairs:
            self.logger.log('Writing: {}...'.format(pair[2]), LogLevel.debug)
            zip.write(os.path.join(target_dir, pair[2]), pair[2])

        self.logger.log('Writing the patch script...', LogLevel.debug)
        zip.write(os.path.join(target_dir, self.script_options['script_name'] + '.cmd'),
                  self.script_options['script_name'] + '.cmd')

        self.logger.log('Writing the executable...', LogLevel.debug)
        zip.write(os.path.join(target_dir, os.path.basename(self.xdelta_location)),
                  os.path.basename(self.xdelta_location))
        zip.close()

    def identify_file_pairs_by_name(self, old_dir, new_dir):
        self.logger.log('Identifying potential file pairs for patching.', LogLevel.debug)

        old_files = os.listdir(str(old_dir))
        new_files = os.listdir(str(new_dir))
        filemap = {}

        for file in [self.create_file_entity(f, old_dir) for f in old_files]:
            if file is not None:
                self.logger.log('Found potential source file: {}'.format(file['filename']), LogLevel.debug)
                self.logger.log('  Group {}, series {}, type {} {}, episode {}, version {}'.format(
                    file['group'],
                    file['name'],
                    file['specifier'],
                    file['ext'],
                    file['ep'],
                    file['ver']
                ), LogLevel.debug)

                key = file.get('key')
                if key in filemap:
                    filemap[key][0].append(file)
                else:
                    filemap[key] = ([file], [])

        for file in [self.create_file_entity(f, new_dir) for f in new_files]:
            if file is not None:
                key = file.get('key')
                if key in filemap:
                    self.logger.log('Found potential target file: {}'.format(file['filename']), LogLevel.debug)
                    self.logger.log('  Group {}, series {}, type {} {}, episode {}, version {}'.format(
                        file['group'],
                        file['name'],
                        file['specifier'],
                        file['ext'],
                        file['ep'],
                        file['ver']
                    ), LogLevel.debug)

                    filemap[key][1].append(file)
                else:
                    # There were no matching files in the old directory, so this won't be a candidate for patching.
                    self.logger.log('Ignoring target file with no equivalent source: {}'.format(file['filename']),
                                    LogLevel.debug)

        # Let's prune those source files that were found that have no target equivalents.
        item_cnt = len(filemap)
        filemap = {k: v for (k, v) in filemap.items() if len(v[1]) >= 1}

        if len(filemap) < item_cnt:
            diff = item_cnt - len(filemap)

            self.logger.log('Dropped {} source candidate{} with no equivalent targets.'.format(
                str(diff), '' if diff == 1 else 's'), LogLevel.debug)

        resolved_relations = []
        for key, group in filemap.items():
            highest_source = max(group[0], key=lambda x: x['ver'])
            highest_target = max(group[1], key=lambda x: x['ver'])

            if highest_source['ver'] == highest_target['ver']:
                self.logger.log('Source and target versions of {} are both {}, ignoring the group.'.format(
                    key, highest_target['ver']
                ), LogLevel.debug)
                continue

            patch_name = self.get_patch_name(highest_source, highest_target)
            resolved_relations.append((highest_source['filename'], highest_target['filename'], patch_name,
                                       highest_target['key'],
                                       self.is_name_windows_safe(os.path.basename(highest_source['filename'])) and
                                       self.is_name_windows_safe(os.path.basename(highest_target['filename']))))
            self.logger.log('Queued: {} -> {}, patch name: {}'.format(
                highest_source['filename'], highest_target['filename'], patch_name
            ), LogLevel.debug)

        return resolved_relations

    @staticmethod
    def cmd_escape(s):
        return re.sub(r'([\[\]\(\)^<>|])', r'^\1', s)

    def get_patch_name(self, source, target):
        try:
            return self.patch_options['filename_pattern'].format(
                raw_group=source['group'],
                raw_name=source['name'],
                raw_ep=source['ep'],
                raw_specifier=source['specifier'],
                raw_ext=source['ext'],
                group=BatchPatch.neutralize_str(source['group']),
                name=BatchPatch.neutralize_str(source['name']),
                ep=BatchPatch.neutralize_str(source['ep']),
                specifier=BatchPatch.neutralize_str(source['specifier']),
                specifier_items=[BatchPatch.neutralize_str(s) for s in (
                    source['specifier'].split() if len(source['specifier']) > 0 else ['']
                )],
                type=BatchPatch.neutralize_str(source['specifier'] + source['ext']),
                ext=BatchPatch.neutralize_str(source['ext']),
                v_old=source['ver'],
                v_new=target['ver'],
                hash_old=source['crc'],
                hash_new=target['crc']
            )
        except KeyError as e:
            self.logger.log('Invalid variable {} in patch name pattern!'.format(e.args[0]), LogLevel.error)
            exit()

    @staticmethod
    def create_file_entity(filename, basedir):
        matcher = re.compile('(?#1. Group shortname)(?:\[([^\]]+?)\] )?'
                             '(?#2. Main name)(.+?)'
                             '(?#3. Episode specifier)(?: - ([a-zA-Z]*\d*))?'
                             '(?#4. Version specifier)(?:v(\d*))?'
                             '(?#5. Other specifiers)(?: \(([^\)]*)\))?'
                             '(?#6. CRC hash)(?: \[([0-9a-fA-F]{8})\])?'
                             '(?#   Eat all extension-looking parts except the last one)(?:\..+)?'
                             '\.'
                             '(?#   Do not match torrents)(?!torrent$)'
                             '(?#7. Get the file extension)([^\.]+)$')

        match = matcher.match(filename)
        if match:
            path = os.path.join(basedir, match.group(0))
            ver = match.group(4)
            if ver is None:
                ver = 1
            specifier = match.group(5)
            if specifier is None:
                specifier = ''

            return {
                "key": "/".join([match.group(x) for x in [1, 2, 3, 5, 7] if isinstance(match.group(x), str)]),
                "ver": int(ver),
                "group": match.group(1),
                "name": match.group(2),
                "ep": match.group(3),
                "specifier": specifier,
                "crc": match.group(6),
                "ext": match.group(7),
                "filename": path
            }
        else:
            return None

    @staticmethod
    def get_default_output_folder():
        return os.path.join(os.getcwd(), 'batch-' + time.strftime('%Y-%m-%d-%H-%M'))

    @staticmethod
    def neutralize_str(name):
        s = unicodedata.normalize('NFKD', name)
        s = u"".join([c for c in s if not unicodedata.combining(c)])
        return re.sub(r'[^a-z0-9_-]', '_', s.casefold())

    unsafe_windows_filenames = [
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]

    @staticmethod
    def is_name_windows_safe(name):
        """ Verifies if the filename can be passed to xdelta on Windows. The user's codepage can be whatever,
            so only accept a subset of the 7-bit ASCII as safe values.
        """
        return name not in BatchPatch.unsafe_windows_filenames and \
               name == re.sub(r'[^ !#$%&()+,\-.0-9;=@A-Z\[\]^_`a-z{}]', r'', name)

    @staticmethod
    def get_install_path():
        return os.path.dirname(os.path.realpath(__file__))


if __name__ == "__main__":
    gettext.install('batchpatch', os.path.join(BatchPatch.get_install_path(), 'i18n'))

    prog = BatchPatch()
    prog.run()
