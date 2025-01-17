#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os as _os
import subprocess
import sys
import re
import argparse

import datetime

class WrappedOS(object):
    str_funcs = ('getenv', 'getcwd',)

    def __init__(self):
        self.os = _os

    def __getattr__(self, name):
        if not sys.version_info >= (3, 0) and name in WrappedOS.str_funcs:
            def wrapped(*args, **kwargs):
                orig = self.os.__getattribute__(name)
                swag=orig(*args, **kwargs)
                if swag is not None:
                    return swag.decode('utf-8')
                else:
                    return None
            return wrapped
        return self.os.__getattribute__(name)

os = WrappedOS()


def warn(msg):
    print('[powerline-shell] ', msg)


class Color:
    # The following link is a pretty good resources for color values:
    # http://www.calmar.ws/vim/color-output.png

    PATH_BG = 237  # dark grey
    PATH_FG = 250  # light grey
    CWD_FG = 254  # nearly-white grey
    CWD_BG = 25  # Arch blue
    SEPARATOR_FG = 244

    TIME_BG = 25#226  # blue (Archlinux)
    TIME_FG = 254#0  # grey

    EXTRA_BG = 238  # yellow
    EXTRA_FG =  252 # black
    EXTRA_SEPC =  244 # black

    REPO_CLEAN_BG = 148  # a light green color
    REPO_CLEAN_FG = 0  # black
    REPO_DIRTY_BG = 161  # pink/red
    REPO_DIRTY_FG = 15  # white

    CMD_PASSED_BG = 236
    CMD_PASSED_FG = 15
    CMD_FAILED_BG = 161
    CMD_FAILED_FG = 15

    SVN_CHANGES_BG = 148
    SVN_CHANGES_FG = 22  # dark green

    VIRTUAL_ENV_BG = 35  # a mid-tone green
    VIRTUAL_ENV_FG = 00


class Powerline:
    symbols = {
        'compatible': {
            'separator': u'\u25B6',
            'separator_thin': u'\u276F',
            'separator_right': u'\u25C0',
            'separator_right_thin': u'\u276E'
        },
        'patched': {
            'separator': u'\uE0B0',
            'separator_thin': u'\uE0B1',
            'separator_right': u'\uE0B2',
            'separator_right_thin': u'\uE0B3'
        }
    }

    color_templates = {
        'bash': '\\[\\e%s\\]',
        'zsh': '%%{%s%%}',
        'bare': '%s',
    }

    root_indicators = {
        'bash': ' \\$ ',
        'zsh': ' $ ',
        'bare': ' $ ',
    }

    def __init__(self, mode, shell, width=0):
        self.shell = shell
        self.color_template = self.color_templates[shell]
        self.root_indicator = self.root_indicators[shell]
        self.reset = self.color_template % '[0m'
        self.separator = Powerline.symbols[mode]['separator']
        self.separator_right = Powerline.symbols[mode]['separator_right']
        self.separator_thin = Powerline.symbols[mode]['separator_thin']
        self.separator_right_thin = Powerline.symbols[mode]['separator_right_thin']
        self.segments = []
        self.segments_right = []
        self.segments_down = []
        self.width=width

    def color(self, prefix, code):
        return self.color_template % ('[%s;5;%sm' % (prefix, code))

    def fgcolor(self, code):
        return self.color('38', code)

    def bgcolor(self, code):
        return self.color('48', code)

    def append(self, segment):
        self.segments.append(segment)

    def append_right(self, segment):
        self.segments_right.append(segment)

    def append_down(self, segment):
        self.segments_down.append(segment)

    def draw(self):
        shifted = self.segments[1:] + [None]
        shifted_right = self.segments_right[1:] + [None]
        shifted_down = self.segments_down[1:] + [None]

        total=0
        total+=sum(c.width() for c in self.segments)
        total+=sum(c.width() for c in self.segments_right)

        spaces=int(self.width)-total
        fold=' ' * spaces
        
        return (
            ''.join((c.draw(n) for c, n in zip(self.segments, shifted)))
            + self.reset + fold + ''.join((c.draw(n) for c, n in zip(reversed(self.segments_right), reversed(shifted_right))))
            + self.reset + "\n" + ''.join((c.draw(n) for c, n in zip(self.segments_down, shifted_down)))
            + self.reset

        )


class Segment:
    def __init__(self, powerline, content, fg, bg, separator=None,
            separator_fg=None, right=False):
        self.powerline = powerline
        self.content = content
        self.fg = fg
        self.bg = bg
        self.separator = separator or powerline.separator
        self.separator_fg = separator_fg or bg
        self.right=right

    def width(self):
        return len(''.join((
            self.content,
            self.separator)))

    def draw(self, next_segment=None):
        if next_segment:
            separator_bg = self.powerline.bgcolor(next_segment.bg)
        else:
            separator_bg = self.powerline.reset

        if self.right == True:
            return ''.join((
                separator_bg,
                self.powerline.fgcolor(self.separator_fg),
                self.separator,
                self.powerline.fgcolor(self.fg),
                self.powerline.bgcolor(self.bg),
                self.content
                
                ))

        return ''.join((
            self.powerline.fgcolor(self.fg),
            self.powerline.bgcolor(self.bg),
            self.content,
            separator_bg,
            self.powerline.fgcolor(self.separator_fg),
            self.separator))


def add_cwd_segment(powerline, cwd, maxdepth, cwd_only=False):
    #powerline.append(' \\w ', 15, 237)
    home = os.getenv('HOME')
    cwd = cwd or os.getenv('PWD')
    #cwd = cwd.decode('utf-8')

    if cwd.find(home) == 0:
        cwd = cwd.replace(home, '~', 1)

    if cwd[0] == '/':
        cwd = cwd[1:]

    names = cwd.split('/')
    if len(names) > maxdepth:
        names = names[:2] + [u'\u2026'] + names[2 - maxdepth:]

    if not cwd_only:
        for n in range(len(names[:-1])):
            sep=powerline.separator_thin
            sepc=Color.SEPARATOR_FG
            if n == len(names)-2:
                sep=powerline.separator
                sepc=Color.PATH_BG
            powerline.append(Segment(powerline, ' %s ' % names[n], Color.PATH_FG,
                Color.PATH_BG, sep, sepc))
    powerline.append(Segment(powerline, ' %s ' % names[-1], Color.CWD_FG,
        Color.CWD_BG))


def get_hg_status():
    has_modified_files = False
    has_untracked_files = False
    has_missing_files = False
    output = subprocess.Popen(['hg', 'status'],
            stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
    for line in output.split('\n'):
        if line == '':
            continue
        elif line[0] == '?':
            has_untracked_files = True
        elif line[0] == '!':
            has_missing_files = True
        else:
            has_modified_files = True
    return has_modified_files, has_untracked_files, has_missing_files


def add_hg_segment(powerline, cwd):
    branch = os.popen('hg branch 2> /dev/null').read().rstrip()
    if len(branch) == 0:
        return False
    bg = Color.REPO_CLEAN_BG
    fg = Color.REPO_CLEAN_FG
    has_modified_files, has_untracked_files, has_missing_files = get_hg_status()
    if has_modified_files or has_untracked_files or has_missing_files:
        bg = Color.REPO_DIRTY_BG
        fg = Color.REPO_DIRTY_FG
        extra = ''
        if has_untracked_files:
            extra += '+'
        if has_missing_files:
            extra += '!'
        branch += (' ' + extra if extra != '' else '')
    powerline.append_right(Segment(powerline, ' %s ' % branch, fg, bg, separator=powerline.separator_right, right=True))
    return True


def get_git_status():
    has_pending_commits = True
    has_untracked_files = False
    origin_position = ""
    output = subprocess.Popen(['git', 'status'],
            stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
    for line in output.split('\n'):
        origin_status = re.findall(
                r"Your branch is (ahead|behind).*?(\d+) comm", line)
        if origin_status:
            origin_position = " %d" % int(origin_status[0][1])
            if origin_status[0][0] == 'behind':
                origin_position += u'\u21E3'
            if origin_status[0][0] == 'ahead':
                origin_position += u'\u21E1'

        if line.find('nothing to commit') >= 0:
            has_pending_commits = False
        if line.find('Untracked files') >= 0:
            has_untracked_files = True
    return has_pending_commits, has_untracked_files, origin_position


def add_git_segment(powerline, cwd):
    #cmd = "git branch 2> /dev/null | grep -e '\\*'"
    p1 = subprocess.Popen(['git', 'branch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.Popen(['grep', '-e', '\\*'], stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0].strip().decode('utf-8')
    if not output:
        return False

    branch = output.rstrip()[2:]
    has_pending_commits, has_untracked_files, origin_position = get_git_status()
    branch += origin_position
    if has_untracked_files:
        branch += ' +'

    bg = Color.REPO_CLEAN_BG
    fg = Color.REPO_CLEAN_FG
    if has_pending_commits:
        bg = Color.REPO_DIRTY_BG
        fg = Color.REPO_DIRTY_FG

    powerline.append_right(Segment(powerline, ' %s ' % branch, fg, bg, separator=powerline.separator_right, right=True))
    return True


def add_svn_segment(powerline, cwd):
    is_svn = subprocess.Popen(['svn', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    is_svn_output = is_svn.communicate()[1].strip().decode('utf-8')
    if len(is_svn_output) != 0:
        return
    '''svn info:
        First column: Says if item was added, deleted, or otherwise changed
        ' ' no modifications
        'A' Added
        'C' Conflicted
        'D' Deleted
        'I' Ignored
        'M' Modified
        'R' Replaced
        'X' a directory pulled in by an svn:externals definition
        '?' item is not under version control
        '!' item is missing (removed by non-svn command) or incomplete
         '~' versioned item obstructed by some item of a different kind
    '''
    #TODO: Color segment based on above status codes
    try:
        #cmd = '"svn status | grep -c "^[ACDIMRX\\!\\~]"'
        p1 = subprocess.Popen(['svn', 'status'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        p2 = subprocess.Popen(['grep', '-c', '^[ACDIMR\\!\\~]'],
                stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0].strip().decode('utf-8')
        if len(output) > 0 and int(output) > 0:
            changes = output.strip()
            powerline.append(Segment(powerline, ' %s ' % changes,
                Color.SVN_CHANGES_FG, Color.SVN_CHANGES_BG))
    except OSError:
        return False
    except subprocess.CalledProcessError:
        return False
    return True

def add_time_segment(powerline, cwd):
        
    now = datetime.datetime.now()
    #stuff = " %d:%d:%d %d.%d.%d " % (now.hour, now.minute, now.second, now.day, now.month, now.year)
    stuff = " %s " % now.strftime("%a %d %H:%M:%S")
    
    powerline.append_right(Segment(powerline, stuff, Color.TIME_FG, Color.TIME_BG, separator=powerline.separator_right, right=True))
    return True

def add_extra_segment(powerline, cwd, extra, color=Color.EXTRA_FG, nol=False):


    sep=powerline.separator_right
    sepc=Color.EXTRA_BG
    if nol:
        sep=powerline.separator_right_thin
        sepc=Color.EXTRA_SEPC

    stuff = " %s " % extra
    
    powerline.append_right(Segment(powerline, stuff, color, Color.EXTRA_BG, separator=sep, separator_fg=sepc, right=True))
    return True

def add_repo_segment(powerline, cwd):
    for add_repo_segment in (add_git_segment, add_svn_segment, add_hg_segment):
        try:
            if add_repo_segment(p, cwd):
                return
        except subprocess.CalledProcessError:
            pass
        except OSError:
            pass


def add_virtual_env_segment(powerline, cwd):
    env = os.getenv("VIRTUAL_ENV")
    if env is None:
        return False

    env_name = os.path.basename(env)
    bg = Color.VIRTUAL_ENV_BG
    fg = Color.VIRTUAL_ENV_FG
    powerline.append_right(Segment(powerline, ' %s ' % env_name, fg, bg, separator=powerline.separator_right, right=True))
    return True


def add_root_indicator(powerline, error):
    bg = Color.CMD_PASSED_BG
    fg = Color.CMD_PASSED_FG
    if int(error) != 0:
        fg = Color.CMD_FAILED_FG
        bg = Color.CMD_FAILED_BG
    powerline.append_down(Segment(powerline, powerline.root_indicator, fg, bg))


def get_valid_cwd():
    """ We check if the current working directory is valid or not. Typically
        happens when you checkout a different branch on git that doesn't have
        this directory.
        We return the original cwd because the shell still considers that to be
        the working directory, so returning our guess will confuse people
    """
    try:
        cwd = os.getcwd()
    except:
        cwd = os.getenv('PWD')  # This is where the OS thinks we are
        parts = cwd.split(os.sep)
        up = cwd
        while parts and not os.path.exists(up):
            parts.pop()
            up = os.sep.join(parts)
        try:
            os.chdir(up)
        except:
            warn("Your current directory is invalid.")
            sys.exit(1)
        warn("Your current directory is invalid. Lowest valid directory: " + up)
    return cwd

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--cwd-only', action='store_true')
    arg_parser.add_argument('--mode', action='store', default='patched')
    arg_parser.add_argument('--extra', action='store', default='')
    arg_parser.add_argument('--shell', action='store', default='bash')
    arg_parser.add_argument('--width', action='store', default=0)
    arg_parser.add_argument('--chroot', action='store', default=0)
    arg_parser.add_argument('prev_error', nargs='?', default=0)
    
    args = arg_parser.parse_args()

    p = Powerline(mode=args.mode, shell=args.shell, width=args.width)
    cwd = get_valid_cwd()
    add_virtual_env_segment(p, cwd)
    #p.append(Segment(p, ' \\u ', 250, 240))
    #p.append(Segment(p, ' \\h ', 250, 238))
    add_cwd_segment(p, cwd, 4, args.cwd_only)
    
    add_time_segment(p, cwd)
    if len(args.extra)>0:
        if args.chroot == "1":
            add_extra_segment(p, cwd, args.extra, nol=True)
        else:
            add_extra_segment(p, cwd, args.extra)

    if args.chroot == "1":
        add_extra_segment(p, cwd, "CHROOT")

    add_repo_segment(p, cwd)
    
    add_root_indicator(p, args.prev_error)
    if sys.version_info >= (3, 0):
        sys.stdout.write(p.draw())
    else:
        sys.stdout.write(p.draw().encode('utf-8'))

# vim: set expandtab:
