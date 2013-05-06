=========================================================================
 hardlink.py – hardlink together identical files in order to save space.
=========================================================================

`hardlink.py` is a tool to hardlink together identical files in order
to save space.  It is a complete rewrite and improvement over the
original hardlink.c code (by Jakub Jelinek at Red Hat).  The purpose
of the two is the same but they do it in vastly different ways.

This code has only been tested on Linux and should work on other Unix
variants.  We have no idea if it will work on Windows as we have never
tested it there and don't know about Windows support for hardlinks.

This code is very useful for people who mirror FTP sites in that it
can save a large amount of space when you have identical files on the
system.

John L. Villalovos (sodarock) first wrote the code in C++ and then
decided to port it to Python.  It was later forked and copied from
Google code to GitHub by Antti Kaihola, and some modifications and
improvements were made there.

Performance is orders of magnitude faster than hardlink.c due to a
more efficient algorithm.  Plus readability is much better too.
