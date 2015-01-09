#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2015 Philemon <mmgen-py@yandex.com>
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
addr.py:  Address generation/display routines for the MMGen suite
"""

import sys
from hashlib import sha256, sha512
from hashlib import new as hashlib_new
from binascii import hexlify, unhexlify

from mmgen.bitcoin import numtowif
# from mmgen.util import msg,qmsg,qmsg_r,make_chksum_N,get_lines_from_file,get_data_from_file,get_extension
from mmgen.util import *
from mmgen.tx import is_mmgen_idx,is_mmgen_seed_id,is_btc_addr,is_wif,get_wif2addr_f
import mmgen.config as g

addrmsgs = {
	'addrfile_header': """
# MMGen address file
#
# This file is editable.
# Everything following a hash symbol '#' is a comment and ignored by {pnm}.
# A text label of {} characters or less may be added to the right of each
# address, and it will be appended to the bitcoind wallet label upon import.
# The label may contain any printable ASCII symbol.
""".strip().format(g.max_addr_label_len,pnm=g.proj_name),
	'no_keyconv_msg': """
Executable '{kcexe}' unavailable. Falling back on (slow) internal ECDSA library.
Please install '{kcexe}' from the {vanityg} package on your system for much
faster address generation.
""".format(kcexe=g.keyconv_exec, vanityg="vanitygen")
}

def test_for_keyconv():

	from subprocess import check_output,STDOUT
	try:
		check_output([g.keyconv_exec, '-G'],stderr=STDOUT)
	except:
		msg(addrmsgs['no_keyconv_msg'])
		return False

	return True


def generate_addrs(seed, addrnums, opts):

	from util import make_chksum_8
	seed_id = make_chksum_8(seed) # Must do this before seed gets clobbered

	if 'a' in opts['gen_what']:
		if g.no_keyconv or test_for_keyconv() == False:
			msg("Using (slow) internal ECDSA library for address generation")
			from mmgen.bitcoin import privnum2addr
			keyconv = False
		else:
			from subprocess import check_output
			keyconv = "keyconv"

	addrnums = sorted(set(addrnums)) # don't trust the calling function
	t_addrs,num,pos,out = len(addrnums),0,0,[]

	w = {
		'ka': ('key/address pair','s'),
		'k':  ('key','s'),
		'a':  ('address','es')
	}[opts['gen_what']]

	from mmgen.addr import AddrInfoEntry,AddrInfo

	while pos != t_addrs:
		seed = sha512(seed).digest()
		num += 1 # round

		if g.debug: print "Seed round %s: %s" % (num, hexlify(seed))
		if num != addrnums[pos]: continue

		pos += 1

		qmsg_r("\rGenerating %s #%s (%s of %s)" % (w[0],num,pos,t_addrs))

		e = AddrInfoEntry()
		e.idx = num

		# Secret key is double sha256 of seed hash round /num/
		sec = sha256(sha256(seed).digest()).hexdigest()
		wif = numtowif(int(sec,16))

		if 'a' in opts['gen_what']:
			if keyconv:
				e.addr = check_output([keyconv, wif]).split()[1]
			else:
				e.addr = privnum2addr(int(sec,16))

		if 'k' in opts['gen_what']: e.wif = wif
		if 'b16' in opts: e.sec = sec

		out.append(e)

	m = w[0] if t_addrs == 1 else w[0]+w[1]
	qmsg("\r%s: %s %s generated%s" % (seed_id,t_addrs,m," "*15))
	a = AddrInfo(has_keys='k' in opts['gen_what'])
	a.initialize(seed_id,out)
	return a

def _parse_addrfile_body(lines,has_keys=False,check=False):

	if has_keys and len(lines) % 2:
		return "Key-address file has odd number of lines"

	ret = []
	while lines:
		a = AddrInfoEntry()
		l = lines.pop(0)
		d = l.split(None,2)

		if not is_mmgen_idx(d[0]):
			return "'%s': invalid address num. in line: '%s'" % (d[0],l)
		if not is_btc_addr(d[1]):
			return "'%s': invalid Bitcoin address" % d[1]

		if len(d) == 3: check_addr_label(d[2])
		else:           d.append("")

		a.idx,a.addr,a.comment = int(d[0]),unicode(d[1]),unicode(d[2])

		if has_keys:
			l = lines.pop(0)
			d = l.split(None,2)

			if d[0] != "wif:":
				return "Invalid key line in file: '%s'" % l
			if not is_wif(d[1]):
				return "'%s': invalid Bitcoin key" % d[1]

			a.wif = unicode(d[1])

		ret.append(a)

	if has_keys and keypress_confirm("Check key-to-address validity?"):
		wif2addr_f = get_wif2addr_f()
		llen = len(ret)
		for n,e in enumerate(ret):
			msg_r("\rVerifying keys %s/%s" % (n+1,llen))
			if e.addr != wif2addr_f(e.wif):
				return "Key doesn't match address!\n  %s\n  %s" % (e.wif,e.addr)
		msg(" - done")

	return ret


def _parse_addrfile(fn,buf=[],has_keys=False,exit_on_error=True):

	if buf: lines = remove_comments(buf.split("\n"))
	else:   lines = get_lines_from_file(fn,"address data",trim_comments=True)

	try:
		sid,obrace = lines[0].split()
	except:
		errmsg = "Invalid first line: '%s'" % lines[0]
	else:
		cbrace = lines[-1]
		if obrace != '{':
			errmsg = "'%s': invalid first line" % lines[0]
		elif cbrace != '}':
			errmsg = "'%s': invalid last line" % cbrace
		elif not is_mmgen_seed_id(sid):
			errmsg = "'%s': invalid Seed ID" % sid
		else:
			ret = _parse_addrfile_body(lines[1:-1],has_keys)
			if type(ret) == list: return sid,ret
			else: errmsg = ret

	if exit_on_error:
		msg(errmsg)
		sys.exit(3)
	else:
		return False


def _parse_keyaddr_file(infile):
	d = get_data_from_file(infile,"%s key-address file data" % g.proj_name)
	enc_ext = get_extension(infile) == g.mmenc_ext
	if enc_ext or not is_utf8(d):
		m = "Decrypting" if enc_ext else "Attempting to decrypt"
		msg("%s key-address file %s" % (m,infile))
		from crypto import mmgen_decrypt_retry
		d = mmgen_decrypt_retry(d,"key-address file")
	return _parse_addrfile("",buf=d,has_keys=True,exit_on_error=False)


class AddrInfoList(object):

	def __init__(self,addrinfo=None):
		self.data = {}

	def seed_ids(self):
		return self.data.keys()

	def addrinfo(self,sid):
		# TODO: Validate sid
		if sid in self.data:
			return self.data[sid]

	def add(self,addrinfo):
		if type(addrinfo) == AddrInfo:
			self.data[addrinfo.seed_id] = addrinfo
			return True
		else:
			msg("Error: object %s is not of type AddrInfo" % repr(addrinfo))
			sys.exit(1)

	def make_reverse_dict(self,btcaddrs):
		d = {}
		for k in self.data.keys():
			d.update(self.data[k].make_reverse_dict(btcaddrs))
		return d

class AddrInfoEntry(object):

	def __init__(self):
		pass

class AddrInfo(object):

	def __init__(self,addrfile="",has_keys=False):
		self.has_keys=has_keys
		if addrfile:
			f = _parse_keyaddr_file if has_keys else _parse_addrfile
			sid,adata = f(addrfile)
			self.initialize(sid,adata)

	def initialize(self,seed_id,addrdata):
		if seed_id in self.__dict__:
			msg("Seed ID already set for object %s" % self)
			return False
		self.seed_id = seed_id
		self.addrdata = addrdata
		self.num_addrs = len(addrdata)
		self.make_addrdata_chksum()
		self.fmt_addr_idxs()
		w = "key" if self.has_keys else "addr"
		qmsg("Computed checksum for %s data %s[%s]: %s" %
				(w,self.seed_id,self.idxs_fmt,self.checksum))
		qmsg("Check this value against your records")

	def idxs(self):
		return [e.idx for e in self.addrdata]

	def addrs(self):
		return ["%s:%s"%(self.seed_id,e.idx) for e in self.addrdata]

	def addrpairs(self):
		return [(e.idx,e.addr) for e in self.addrdata]

	def btcaddrs(self):
		return [e.addr for e in self.addrdata]

	def comments(self):
		return [e.comment for e in self.addrdata]

	def entry(self,idx):
		for e in self.addrdata:
			if idx == e.idx: return e

	def btcaddr(self,idx):
		for e in self.addrdata:
			if idx == e.idx: return e.addr

	def comment(self,idx):
		for e in self.addrdata:
			if idx == e.idx: return e.comment

	def set_comment(self,idx,comment):
		for e in self.addrdata:
			if idx == e.idx: e.comment = comment

	def make_reverse_dict(self,btcaddrs):
		d = {}
		for e in self.addrdata:
			try:
				i = btcaddrs.index(e.addr)
				d[btcaddrs[i]] = ("%s:%s"%(self.seed_id,e.idx),e.comment)
			except: pass
		return d

	def make_addrdata_chksum(self):
		nchars = 24
		lines = [" ".join([str(e.idx),e.addr]+([e.wif] if self.has_keys else []))
						for e in self.addrdata]
		self.checksum = make_chksum_N(" ".join(lines), nchars, sep=True)

	def fmt_data(self):

		fs = "  {:<%s}  {}" % len(str(self.addrdata[-1].idx))

		# Header
		have_addrs,have_wifs,have_secs = True,True,True

		try: self.addrdata[0].addr
		except: have_addrs = False

		try: self.addrdata[0].wif
		except: have_wifs = False

		try: self.addrdata[0].sec
		except: have_secs = False

		if not (have_addrs or have_wifs):
			msg("No addresses or wifs in addr data!")
			sys.exit(3)

		out = []
		if have_addrs:
			from mmgen.addr import addrmsgs
			out.append(addrmsgs['addrfile_header'] + "\n")
			w = "Key-address" if have_wifs else "Address"
			out.append("# {} data checksum for {}[{}]: {}".format(
						w, self.seed_id, self.idxs_fmt, self.checksum))
			out.append("# Record this value to a secure location\n")

		out.append("%s {" % self.seed_id)

		for e in self.addrdata:
			if have_addrs:  # First line with idx
				out.append(fs.format(e.idx, e.addr))
			else:
				out.append(fs.format(e.idx, "wif: "+e.wif))

			if have_wifs:   # Subsequent lines
				if have_secs:
					out.append(fs.format("", "hex: "+e.sec))
				if have_addrs:
					out.append(fs.format("", "wif: "+e.wif))

		out.append("}")

		return "\n".join(out)

	def fmt_addr_idxs(self):

		try: int(self.addrdata[0].idx)
		except:
			self.idxs_fmt = "(no idxs)"
			return

		addr_idxs = [e.idx for e in self.addrdata]
		prev = addr_idxs[0]
		ret = prev,

		for i in addr_idxs[1:]:
			if i == prev + 1:
				if i == addr_idxs[-1]: ret += "-", i
			else:
				if prev != ret[-1]: ret += "-", prev
				ret += ",", i
			prev = i

		self.idxs_fmt = "".join([str(i) for i in ret])
