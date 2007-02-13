#!/usr/bin/python

import getopt, os, re, stat, sys, time

# hardlink - Goes through a directory structure and creates hardlinks for
# files which are identical.
#
# Copyright (C) 2003 - 2007  John L. Villalovos, Hillsboro, Oregon
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 59
# Temple Place, Suite 330, Boston, MA  02111-1307, USA.
#
#
# ------------------------------------------------------------------------
# John Villalovos
# email: john@sodarock.com
# http://www.sodarock.com/
#
# Inspiration for this program came from the hardlink.c code. I liked what it
# did but did not like the code itself, to me it was very unmaintainable.  So I
# rewrote in C++ and then I rewrote it in python.  In reality this code is
# nothing like the original hardlink.c, since I do things quite differently.
# Even though this code is written in python the performance of the python
# version is much faster than the hardlink.c code, in my limited testing.  This
# is mainly due to use of different algorithms.
#
# Original inspirational hardlink.c code was written by:  Jakub Jelinek
# <jakub@redhat.com>
#
# ------------------------------------------------------------------------


# Hash functions
# Create a hash from a file's size and time values
def hash_size_time(size, time):
    return (size ^ time) & (MAX_HASHES - 1);

def hash_size(size):
    return (size) & (MAX_HASHES - 1);

def hash_value(size, time):
    if gOptions.isIgnoretimestamp():
        return hash_size(size)
    else:
        return hash_size_time(size,time)

# If two files have the same inode and are on the same device then they are
# already hardlinked.
def isAlreadyHardlinked(
    st1,     # first file's status
    st2 ):    # second file's status
    result = (
                      (st1[stat.ST_INO] == st2[stat.ST_INO]) and # Inodes equal
                      (st1[stat.ST_DEV] == st2[stat.ST_DEV])     # Devices equal
                  );
    return result

# if a file is eligibile for hardlinking.  Files will only be considered for
# hardlinking if this function returns true.
def eligibleForHardlink(
    st1,        # first file's status
    st2):       # second file's status

    result = (
            # Must meet the following
            # criteria:
            (not isAlreadyHardlinked(st1, st2)) and         # NOT already hard linked
            (st1[stat.ST_SIZE] == st2[stat.ST_SIZE]) and    # size is the same
            (st1[stat.ST_SIZE] != 0 ) and                   # size is not zero
            (st1[stat.ST_MODE] == st2[stat.ST_MODE]) and    # file mode is the same
            (st1[stat.ST_UID] == st2[stat.ST_UID]) and      # owner user id is the same
            (st1[stat.ST_GID] == st2[stat.ST_GID]) and      # owner group id is the same
            ((st1[stat.ST_MTIME] == st2[stat.ST_MTIME]) or  # modified time is the same
              (gOptions.isIgnoretimestamp())) and           # OR date hashing is off
            (st1[stat.ST_DEV] == st2[stat.ST_DEV])          # device is the same
        )
    if None:
    # if not result:
        print "\n***\n", st1
        print st2
        print "Already hardlinked: %s" % (not isAlreadyHardlinked(st1, st2))
        print "Modes:", st1[stat.ST_MODE], st2[stat.ST_MODE]
        print "UIDs:", st1[stat.ST_UID], st2[stat.ST_UID]
        print "GIDs:", st1[stat.ST_GID], st2[stat.ST_GID]
        print "SIZE:", st1[stat.ST_SIZE], st2[stat.ST_SIZE]
        print "MTIME:", st1[stat.ST_MTIME], st2[stat.ST_MTIME]
        print "Ignore date:", gOptions.isIgnoretimestamp()
        print "Device:", st1[stat.ST_DEV], st2[stat.ST_DEV]
    return result


def areFileContentsEqual(filename1, filename2):
    """Determine if the contents of two files are equal.
    **!! This function assumes that the file sizes of the two files are
    equal."""
    # Open our two files
    file1 = open(filename1,'rb')
    file2 = open(filename2,'rb')
    # Make sure open succeeded
    if not (file1 and file2):
        print "Error opening file in areFileContentsEqual"
        print "Was attempting to open:"
        print "file1: %s" % filename1
        print "file2: %s" % filename2
        result = None
    else:
        if gOptions.getVerboselevel() >= 1:
            print "Comparing: %s" % filename1
            print "     to  : %s" % filename2
        buffer_size = 1024*1024
        while 1:
            buffer1 = file1.read(buffer_size)
            buffer2 = file2.read(buffer_size)
            if buffer1 != buffer2:
                result = None
                break
            if not buffer1:
                result = 1
                break
        gStats.didComparison()
    return result

# Determines if two files should be hard linked together.
def areFilesHardlinkable(file_info_1, file_info_2):
    filename1 = file_info_1[0]
    stat_info_1 = file_info_1[1]
    filename2 = file_info_2[0]
    stat_info_2 = file_info_2[1]
    # See if the files are eligible for hardlinking
    if eligibleForHardlink(stat_info_1, stat_info_2):
        # Now see if the contents of the file are the same.  If they are then
        # these two files should be hardlinked.
        if not gOptions.isEqualfilenames():
            # By default we don't care if the filenames are equal
            result = areFileContentsEqual(filename1, filename2)
        else:
            # Make sure the filenames are the same, if so then compare content
            basename1 = os.path.basename(filename1)
            basename2 = os.path.basename(filename2)
            if basename1 == basename2:
                result = areFileContentsEqual(filename1, filename2)
            else:
                result = None
    else:
        result = None
    return result

# Hardlink two files together
def hardlinkfiles(sourcefile, destfile, stat_info):
    # rename the destination file to save it
    temp_name = destfile + ".$$$___cleanit___$$$"
    try:
        if not gOptions.isDryrun():
            os.rename(destfile, temp_name)
    except OSError, error:
        print "Failed to rename: %s to %s" % (destfile, temp_name)
        print error
        result = None
    else:
        # Now link the sourcefile to the destination file
        try:
            if not gOptions.isDryrun():
                os.link(sourcefile, destfile)
        except:
            print "Failed to hardlink: %s to %s" % (sourcefile, destfile)
            # Try to recover
            try:
                os.rename(temp_name, destfile)
            except:
                print "BAD BAD - failed to rename back %s to %s" (temp_name, destfile)
            result = None
        else:
            # hard link succeeded
            # Delete the renamed version since we don't need it.
            if not gOptions.isDryrun():
                os.unlink ( temp_name)
            # update our stats
            gStats.didHardlink(sourcefile, destfile, stat_info)
            if gOptions.getVerboselevel() >= 1:
                if gOptions.isDryrun():
                    print "Did NOT link.  Dry run"
                size = stat_info[stat.ST_SIZE]
                print "Linked: %s" % sourcefile
                print"     to: %s, saved %s" % (destfile, size)
            result = 1
    return result

def hardlink_identical_files(directories, filename):
    """
    The purpose of this function is to hardlink files together if the files are
    the same.  To be considered the same they must be equal in the following
    criteria:
          * file mode
          * owner user id
          * owner group id
          * file size
          * modified time (optional)
          * file contents

    Also, files will only be hardlinked if they are on the same device.  This
    is because hardlink does not allow you to hardlink across file systems.

    The basic idea on how this is done is as follows:

        Walk the directory tree building up a list of the files.

     For each file, generate a simple hash based on the size and modified time.

     For any other files which share this hash make sure that they are not
     identical to this file.  If they are identical than hardlink the files.

     Add the file info to the list of files that have the same hash value."""

    for exclude in gOptions.getExcludes():
        if re.search(exclude, filename):
            return
    try:
        stat_info = os.stat(filename)
    except OSError:
        # Python 1.5.2 doesn't handle 2GB+ files well :(
        print "Unable to get stat info for: %s" % filename
        print "If running Python 1.5 this could be because the file is greater than 2 Gibibytes"
        return
    if not stat_info:
        # We didn't get the file status info :(
        return

    # Is it a directory?
    if stat.S_ISDIR(stat_info[stat.ST_MODE]):
        # If it is a directory then add it to the list of directories.
        directories.append(filename)
    # Is it a regular file?
    elif stat.S_ISREG(stat_info[stat.ST_MODE]):
        # Create the hash for the file.
        file_hash = hash_value( stat_info[stat.ST_SIZE], stat_info[stat.ST_MTIME] )
        # Bump statistics count of regular files found.
        gStats.foundRegularFile()
        if gOptions.getVerboselevel() >= 2:
            print "File: %s" % filename
        work_file_info = (filename, stat_info)
        if file_hashes.has_key(file_hash):
            # We have file(s) that have the same hash as our current file.
            # Let's go through the list of files with the same hash and see if
            # we are already hardlinked to any of them.
            for (temp_filename,temp_stat_info) in file_hashes[file_hash]:
                if isAlreadyHardlinked(stat_info,temp_stat_info):
                    gStats.foundHardlink(temp_filename,filename,
                        temp_stat_info)
                    break
            else:
                # We did not find this file as hardlinked to any other file
                # yet.  So now lets see if our file should be hardlinked to any
                # of the other files with the same hash.
                for (temp_filename,temp_stat_info) in file_hashes[file_hash]:
                    if areFilesHardlinkable(work_file_info, (temp_filename, temp_stat_info)):
                        hardlinkfiles(temp_filename, filename, temp_stat_info)
                        break
                else:
                    # The file should NOT be hardlinked to any of the other
                    # files with the same hash.  So we will add it to the list
                    # of files.
                    file_hashes[file_hash].append(work_file_info)
        else:
            # There weren't any other files with the same hash value so we will
            # create a new entry and store our file.
            file_hashes[file_hash] = [work_file_info]


class cStatistics:
    def __init__(self):
        self.dircount = 0L                  # how many directories we find
        self.regularfiles = 0L              # how many regular files we find
        self.comparisons = 0L               # how many file content comparisons
        self.hardlinked_thisrun = 0L        # hardlinks done this run
        self.hardlinked_previously = 0L;    # hardlinks that are already existing
        self.bytes_saved_thisrun = 0L       # bytes saved by hardlinking this run
        self.bytes_saved_previously = 0L    # bytes saved by previous hardlinks
        self.hardlinkstats = []             # list of files hardlinked this run
        self.starttime = time.time()        # track how long it takes
        self.previouslyhardlinked = {}      # list of files hardlinked previously

    def foundDirectory(self):
        self.dircount = self.dircount + 1
    def foundRegularFile(self):
        self.regularfiles = self.regularfiles + 1
    def didComparison(self):
        self.comparisons = self.comparisons + 1
    def foundHardlink(self,sourcefile, destfile, stat_info):
        filesize = stat_info[stat.ST_SIZE]
        self.hardlinked_previously = self.hardlinked_previously + 1
        self.bytes_saved_previously = self.bytes_saved_previously + filesize
        if not self.previouslyhardlinked.has_key(sourcefile):
            self.previouslyhardlinked[sourcefile] = (stat_info,[destfile])
        else:
            self.previouslyhardlinked[sourcefile][1].append(destfile)
    def didHardlink(self,sourcefile,destfile,stat_info):
        filesize = stat_info[stat.ST_SIZE]
        self.hardlinked_thisrun = self.hardlinked_thisrun + 1
        self.bytes_saved_thisrun = self.bytes_saved_thisrun + filesize
        self.hardlinkstats.append((sourcefile, destfile))
    def printStats(self):
        print "\n"
        print "Hard linking Statistics:"
        # Print out the stats for the files we hardlinked, if any
        if self.previouslyhardlinked and gOptions.printPrevious():
            keys = self.previouslyhardlinked.keys()
            keys.sort()
            print "Files Previously Hardlinked:"
            for key in keys:
                stat_info, file_list = self.previouslyhardlinked[key]
                size = stat_info[stat.ST_SIZE]
                print "Hardlinked together: %s" % key
                for filename in file_list:
                    print "                   : %s" % filename
                print "Size per file: %s  Total saved: %s" % (size,
                                    size * len(file_list))
            print
        if self.hardlinkstats:
            if gOptions.isDryrun():
                print "Statistics reflect what would have happened if not a dry run"
            print "Files Hardlinked this run:"
            for (source,dest) in self.hardlinkstats:
                print"Hardlinked: %s" % source
                print"        to: %s" % dest
            print
        print "Directories           : %s" % self.dircount
        print "Regular files         : %s" % self.regularfiles
        print "Comparisons           : %s" % self.comparisons
        print "Hardlinked this run   : %s" % self.hardlinked_thisrun
        print "Total hardlinks       : %s" % (self.hardlinked_previously + self.hardlinked_thisrun)
        print "Bytes saved this run  : %s (%s)" % (self.bytes_saved_thisrun, humanize_number(self.bytes_saved_thisrun))
        totalbytes = self.bytes_saved_thisrun + self.bytes_saved_previously;
        print "Total bytes saved     : %s (%s)" % (totalbytes, humanize_number(totalbytes))
        print "Total run time        : %s seconds" % (time.time() - self.starttime)



def humanize_number( number ):
    if number  > 1024 * 1024 * 1024:
        return ("%.3f gibibytes" % (number / (1024.0 * 1024 * 1024)))
    if number  > 1024 * 1024:
        return ("%.3f mibibytes" % (number / (1024.0 * 1024)))
    if number  > 1024:
        return ("%.3f kibibytes" % (number / 1024.0))
    return ("%d bytes" % number)



class cOptions:
    def __init__(self):
        self.notimestamp = None
        self.samename = None
        self.printstats = 1
        self.verbose = 1
        self.dryrun = None
        self.zerosize = None
        self.exclude = []
        self.printprevious = None

    def parsearguments(self,arg_list):
        # TODO: Probably should change this to use optparse but I want it to be
        # compatible with Python 1.5 at the moment, but soon I won't care about
        # that
        short_options = 'fnpqtv:x:'
        long_options = [ 'timestamp-ignore', 'filenames-equal',
            'dry-run', 'no-stats', 'print-previous', 'verbose=',
            'version', 'exclude=' ]
        try:
            optlist,args = getopt.getopt(arg_list[1:],short_options,long_options)
        except getopt.GetoptError, error:
            print "Error in argument parsing: %s" %  error
            print
            self.arghelp()
            sys.exit(1)
        for opt, value in optlist:
            if opt == "-f" or opt== "--filename-ignore":
                self.samename = 1
            elif opt == "-n" or opt == "--dry-run":
                self.dryrun = 1
            elif opt == "-q" or opt == "--no-stats":
                self.printstats = None
            elif opt == "-t" or opt == "--timestamp-ignore":
                self.notimestamp = 1
            elif opt == "-v" or opt == "--verbose":
                self.verbose = int(value)
            elif opt == "--version":
                self.printversion()
                sys.exit(0)
            elif opt == "-x" or opt == "--exclude":
                self.exclude.append(value)
            elif opt == "-p" or opt == "--print-previous":
                self.printprevious = 1
            else:
                print "Error: Unknown option: (%s, %s)" % (opt,value)
                sys.exit(1)
        if not args:
            print "Error in argument parsing: No directories specified"
            print
            self.arghelp()
            sys.exit(1)
        else:
            for x in range(0, len(args)):
                args[x] = os.path.abspath(os.path.expanduser(args[x]))
        return args
    def printversion(self):
        print "hardlink.py, Version %s" % VERSION
        print "Copyright (C) 2003 - 2006 John L. Villalovos."
        print "email: software@sodarock.com"
        print "web: http://www.sodarock.com/"
        print """
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; version 2 of the License.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc., 59 Temple
Place, Suite 330, Boston, MA  02111-1307, USA.
"""

    def arghelp(self):
        print "Usage: hardlink.py [OPTION]... [DIRECTORY]..."
        print "Hardlink files together that are the same in the directory tree"
        print
        print "Mandatory arguments to long options are mandatory for short options too."
        print "  -f, --filenames-equal   Filenames have to be identical"
        print "  -n, --dry-run           Do NOT actually hardlink files"
        print "  -p, --print-previous    Print previously created hardlinks"
        print "  -q, --no-stats          Do not print the statistics"
        print "  -t, --timestamp-ignore  File modification times do NOT have to be identical"
        print "  -v, --verbose=NUM       Verbosity level (default 1)"
        print "  -x, --exclude=REGEX     Regular Expression used to exclude files/dirs"
        print "                          This is treated as a Regular Expression."
        print "                          ~user/ directory syntax is NOT supported."
        print "                          Example: ~ftp/pub/ignore/ will NOT work."
        print "                          Example: '^/var/ftp/pub/ignore/' will work."
        print ""
        print "  The -t flag is only recommended if you have a static repository, since"
        print "  if you are doing an RSYNC the next pass will redownload the files,"
        print "  since the timestamps are different."
    def getPrintstats(self):
        return self.printstats
    def getVerboselevel(self):
        return self.verbose
    def isIgnoretimestamp(self):
        return self.notimestamp
    def isEqualfilenames(self):
        return self.samename
    def isDryrun(self):
        return self.dryrun
    def getExcludes(self):
        return self.exclude
    def printPrevious(self):
        return self.printprevious


# Start of global declarations
debug = None
debug1 = None

MAX_HASHES = 128 * 1024

gStats = cStatistics()
gOptions  = cOptions()

file_hashes = {}

VERSION = "0.02 - 13-Dec-2005"

def main():
    # Parse our argument list and get our list of directories
    directories = gOptions.parsearguments(sys.argv)
    # Compile up our regexes ahead of time
    MIRROR_PL_REGEX = re.compile(r'^\.in\.')
    RSYNC_TEMP_REGEX = re.compile((r'^\..*\.\?{6,6}$'))
    # Now go through all the directories that have been added.
    # NOTE: hardlink_identical_files() will add more directories to the
    #       directories list as it finds them.
    while directories:
        # Get the last directory in the list
        directory = directories[-1] + '/'
        del directories[-1]
        if not os.path.isdir(directory):
            print "%s is NOT a directory!" % directory
        else:
            gStats.foundDirectory()
            # Loop through all the files in the directory
            try:
                dir_entries = os.listdir(directory)
            except OSError:
                print "Error: Unable to do an os.listdir on: %s  Skipping..." % directory
                continue
            for entry in dir_entries:
                pathname = os.path.normpath(os.path.join(directory,entry))
                # Look at files/dirs beginning with "."
                if entry[0] == ".":
                    # Ignore any mirror.pl files.  These are the files that
                    # start with ".in."
                    if MIRROR_PL_REGEX.match(entry):
                        continue
                    # Ignore any RSYNC files.  These are files that have the
                    # format .FILENAME.??????
                    if RSYNC_TEMP_REGEX.match(entry):
                        continue
                if os.path.islink(pathname):
                    if debug1: print "%s: is a symbolic link, ignoring" % pathname
                    continue
                if debug1 and os.path.isdir(pathname):
                    print "%s is a directory!" % pathname
                hardlink_identical_files(directories, pathname)
    if gOptions.getPrintstats():
        gStats.printStats()

if __name__ == '__main__':
    main()
