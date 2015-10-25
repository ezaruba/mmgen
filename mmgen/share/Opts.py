#!/usr/bin/env python
#
# Opts.py, an options parsing library for Python.  Copyright (C) 2014 by
# Philemon <mmgen-py@yandex.com>.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, getopt

def usage(opts_data):
	print "USAGE: %s %s" % (opts_data['prog_name'], opts_data['usage'])
	sys.exit(2)

def print_help(opts_data):
	pn = opts_data['prog_name']
	pn_len = str(len(pn)+2)
	print ("  %-"+pn_len+"s %s") % (pn.upper()+":", opts_data['desc'].strip())
	print ("  %-"+pn_len+"s %s %s")%("USAGE:", pn, opts_data['usage'].strip())
	sep = "\n    "
	print "  OPTIONS:"+sep+"%s" % sep.join(opts_data['options'].strip().splitlines())
	if "notes" in opts_data:
		print "  %s" % "\n  ".join(opts_data['notes'][1:-1].splitlines())


def process_opts(argv,opts_data,short_opts,long_opts):

	import os
	opts_data['prog_name'] = os.path.basename(sys.argv[0])
	long_opts  = [i.replace("_","-") for i in long_opts]

	try: cl_opts,args = getopt.getopt(argv[1:], short_opts, long_opts)
	except getopt.GetoptError as err:
		print str(err); sys.exit(2)

	opts,short_opts_l = {},[]

	for i in short_opts:
		if i == ":": short_opts_l[-1] += i
		else:        short_opts_l     += i

	for opt, arg in cl_opts:
		if   opt in ("-h","--help"): print_help(opts_data); sys.exit()
		elif opt[:2] == "--" and opt[2:] in long_opts:
			opts[opt[2:].replace("-","_")] = True
		elif opt[:2] == "--" and opt[2:]+"=" in long_opts:
			opts[opt[2:].replace("-","_")] = arg
		elif opt[0] == "-" and opt[1]     in short_opts_l:
			opts[long_opts[short_opts_l.index(opt[1:])].replace("-","_")] = True
		elif opt[0] == "-" and opt[1:]+":" in short_opts_l:
			opts[long_opts[short_opts_l.index(
					opt[1:]+":")][:-1].replace("-","_")] = arg
		else: assert False, "Invalid option"

	if 'sets' in opts_data:
		for o_in,v_in,o_out,v_out in opts_data['sets']:
			if o_in in opts:
				v = opts[o_in]
				if (v and v_in == bool) or v == v_in:
					if o_out in opts and opts[o_out] != v_out:
						sys.stderr.write(
				"Option conflict:\n  --%s=%s, with\n  --%s=%s\n" % (
					o_out.replace("_","-"),opts[o_out],
					o_in.replace("_","-"),opts[o_in]
				))
						sys.exit(1)
					else:
						opts[o_out] = v_out

	return opts,args


def parse_opts(argv,opts_data,opt_filter=None):

	import re
	pat = r"^-([a-zA-Z0-9]), --([a-zA-Z0-9-]{2,64})(=| )(.+)"
	od,skip = [],True

	for l in opts_data['options'].strip().splitlines():
		m = re.match(pat,l)
		if m:
			skip = True if (opt_filter and m.group(1) not in opt_filter) else False
			app = [':','='] if (m.group(3) == '=') else ['','']
			od.append(list(m.groups()) + app + [skip])
		else:
			if not skip: od[-1][3] += "\n" + l

	opts_data['options'] = "\n".join(
		["-{}, --{} {}".format(d[0],d[1],d[3]) for d in od if d[6] == False]
	)
	short_opts    = "".join([d[0]+d[4] for d in od if d[6] == False])
	long_opts     = [d[1].replace("-","_")+d[5] for d in od if d[6] == False]
	skipped_opts  = [d[1].replace("-","_") for d in od if d[6] == True]

	opts,args = process_opts(argv,opts_data,short_opts,long_opts)

	return opts,args,short_opts,long_opts,skipped_opts
