#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2014 Philemon <mmgen-py@yandex.com>
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

"""
mmgen-walletgen: Generate an MMGen deterministic wallet
"""

import sys, os
from hashlib import sha256

import mmgen.config as g
from mmgen.Opts import *
from mmgen.license import *
from mmgen.util import *
from mmgen.crypto import *

help_data = {
	'prog_name': g.prog_name,
	'desc':    "Generate an {} deterministic wallet".format(g.proj_name),
	'usage':   "[opts] [infile]",
	'options': """
-h, --help                 Print this help message
-d, --outdir=           d  Specify an alternate directory 'd' for output
-e, --echo-passphrase      Print passphrase to screen when typing it
-H, --show-hash-presets    Show information on available hash presets
-l, --seed-len=         n  Create seed of length 'n'. Options: {seed_lens}
                           (default: {g.seed_len})
-L, --label=            l  Label to identify this wallet (32 chars max.
                           Allowed symbols: A-Z, a-z, 0-9, " ", "_", ".")
-p, --hash-preset=      p  Use scrypt.hash() parameters from preset 'p'
                           (default: '{g.hash_preset}')
-P, --passwd-file=      f  Get MMGen wallet passphrase from file 'f'
-q, --quiet                Produce quieter output; overwrite files without
                           prompting
-r, --usr-randchars=    n  Get 'n' characters of additional randomness from
                           user (min={g.min_urandchars}, max={g.max_urandchars})
-v, --verbose              Produce more verbose output

-b, --from-brain=      l,p Generate wallet from a user-created passphrase,
                           i.e. a "brainwallet", using seed length 'l' and
                           hash preset 'p' (comma-separated)
-g, --from-incog           Generate wallet from an incognito-format wallet
-m, --from-mnemonic        Generate wallet from an Electrum-like mnemonic
-s, --from-seed            Generate wallet from a seed in .{g.seed_ext} format
""".format(seed_lens=",".join([str(i) for i in g.seed_lens]), g=g),
	'notes': """

By default (i.e. when invoked without any of the '--from-<what>' options),
{g.prog_name} generates a wallet based on a random seed.

Data for the --from-<what> options will be taken from <infile> if <infile>
is specified.  Otherwise, the user will be prompted to enter the data.

For passphrases all combinations of whitespace are equal, and leading and
trailing space are ignored.  This permits reading passphrase data from a
multi-line file with free spacing and indentation.  This is particularly
convenient for long brainwallet passphrases, for example.

Since good randomness is particularly important when generating wallets,
the '--usr-randchars' option is turned on by default to gather additional
entropy from the user.  If you fully trust your OS's random number gener-
ator and wish to disable this option, specify '-r0' on the command line.

BRAINWALLET NOTE:

As brainwallets require especially strong hashing to thwart dictionary
attacks, the brainwallet hash preset must be specified by the user, using
the 'p' parameter of the '--from-brain' option.  This preset should be
stronger than the one used for hashing the seed (i.e. the default value or
the one specified in the '--hash-preset' option).

The '--from-brain' option also requires the user to specify a seed length
(the 'l' parameter), which overrides both the default and any one given in
the '--seed-len' option.

For a brainwallet passphrase to always generate the same keys and
addresses, the same 'l' and 'p' parameters to '--from-brain' must be used
in all future invocations with that passphrase.
""".format(g=g)
}

opts,cmd_args = parse_opts(sys.argv,help_data)

if 'show_hash_presets' in opts: show_hash_presets()
if opts['usr_randchars'] == -1: opts['usr_randchars'] = g.usr_randchars_dfl

if g.debug: show_opts_and_cmd_args(opts,cmd_args)

if len(cmd_args) == 1:
	infile = cmd_args[0]
	check_infile(infile)
	ext = infile.split(".")[-1]
	ok_exts = g.seedfile_exts
	for e in ok_exts:
		if e == ext: break
	else:
		msg(
"Input file must have one of the following extensions: .%s" % ", .".join(ok_exts))
		sys.exit(1)
elif len(cmd_args) == 0:
	infile = ""
else: usage(help_data)

# Begin execution

do_license_msg()

if 'from_brain' in opts and not g.quiet:
	confirm_or_exit(cmessages['brain_warning'].format(
			g.proj_name, *get_from_brain_opt_params(opts)),
		"continue")

for i in 'from_mnemonic','from_brain','from_seed','from_incog':
	if infile or (i in opts):
		seed = get_seed_retry(infile,opts)
		if "from_incog" in opts or get_extension(infile) == g.incog_ext:
			qmsg(cmessages['incog'] % make_chksum_8(seed))
		else: qmsg("")
		break
else:
	# Truncate random data for smaller seed lengths
	seed = sha256(get_random(128,opts)).digest()[:opts['seed_len']/8]

salt = sha256(get_random(128,opts)).digest()[:g.salt_len]

qmsg(cmessages['choose_wallet_passphrase'] % opts['hash_preset'])

passwd = get_new_passphrase("new {} wallet".format(g.proj_name), opts)

key = make_key(passwd, salt, opts['hash_preset'])

enc_seed = encrypt_seed(seed, key)

write_wallet_to_file(seed,passwd,make_chksum_8(key),salt,enc_seed,opts)