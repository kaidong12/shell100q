#!/usr/bin/python
import os
import re
import sys

# This script is used for automatically adding INCLUSIVE clauses in StoRs 
# for a DDL file. It helps to migrate databases created prior to the new 
# default (right edge exclusive) in Prime Analytics 1.1.

patterns = [[r"(?is)(<\s*(?:slices|visible|landmark|session|same|per)\s+(?:(?!\b(?:align|inclusive|exclusive)\b).)+?)(\s+\bon\b\s+\w+\s*>|\s*>)",
	     r"\1 INCLUSIVE\2"]]

def file_replace(fname, fname_out, pat, replace):
	# perform replace operation according to the pattern.
	text = open(fname).read()
	out = open(fname_out, "w")
	out.write(re.sub(pat, replace, text))
	out.close()

if len(sys.argv) != 3:
	u = "Usage: sqlupgrade <inputfile> <outputfile>\n"
	sys.stderr.write(u)
	sys.exit(1)

for pat in patterns:
	file_replace(sys.argv[1], sys.argv[2], pat[0], pat[1])

