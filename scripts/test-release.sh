#!/bin/bash
# Tested on Linux, MinGW-64

PROGNAME=$(basename $0)
while getopts hint OPT
do
	case "$OPT" in
	h)  printf "  %-16s Test MMGen release\n" "${PROGNAME^^}:"
		echo   "  USAGE:           $PROGNAME [options] branch [tests]"
		echo   "  OPTIONS: '-h'  Print this help message"
		echo   "           '-i'  Install only; don't run tests"
		echo   "           '-n'  Don't install; test in place"
		echo   "           '-t'  Print the tests without running them"
		echo   "  AVAILABLE TESTS:"
		echo   "     1 - main"
		echo   "     2 - tooltest"
		echo   "     3 - gentest"
		echo   "     4 - regtest"
		echo   "  By default, all tests are run"
		exit ;;
	i)  INSTALL_ONLY=1 ;;
	n)  NO_INSTALL=1 ;;
	t)  TESTING=1 ;;
	*)  exit ;;
	esac
done

shift $((OPTIND-1))

set -e
GREEN="\e[32;1m" YELLOW="\e[33;1m" RESET="\e[0m"
BRANCH=$1; shift
REFDIR=test/ref
if uname -a | grep -qi mingw; then SUDO='' MINGW=1; else SUDO='sudo' MINGW=''; fi

function check {
	[ "$BRANCH" ] || { echo 'No branch specified.  Exiting'; exit; }
	[ "$(git diff $BRANCH)" == "" ] || {
		echo "Unmerged changes from branch '$BRANCH'. Exiting"
		exit
	}
	git diff $BRANCH >/dev/null 2>&1 || exit
}

function install {
	set -x
	eval "$SUDO rm -rf .test-release"
	git clone --branch $BRANCH --single-branch . .test-release
	cd .test-release
	./setup.py sdist
	mkdir pydist && cd pydist
	if [ "$MINGW" ]; then unzip ../dist/mmgen-*.zip; else tar zxvf ../dist/mmgen-*gz; fi
	cd mmgen-*
	scripts/deinstall.sh

	[ "$MINGW" ] && ./setup.py build --compiler=mingw32
	eval "$SUDO ./setup.py install"
}
[ -z "$TESTING" ] && LS='\n'
function do_test {
	set +x
	for i in "$@"; do
		echo -e "$LS${GREEN}Running:$RESET $YELLOW$i$RESET"
		[ "$TESTING" ] || eval "$i"
	done
}

T1=('test/test.py -On'
	'test/test.py -On --segwit dfl_wallet main ref ref_other'
	'test/test.py -On --coin=bch dfl_wallet main ref ref_other'
	'test/test.py -On --segwit-random dfl_wallet main')
T2=('test/tooltest.py' 'test/tooltest.py --testnet=1') # tooltest tests both segwit and non-segwit
T3=("test/gentest.py -q 2 $REFDIR/btcwallet.dump"
	"test/gentest.py -q --testnet=1 2 $REFDIR/btcwallet-testnet.dump"
	'test/gentest.py -q 1:2 10'
	'test/gentest.py -q --segwit 1:2 10'
#	"scripts/tx-old2new.py -S $REFDIR/tx_*raw >/dev/null 2>&1"
	"scripts/compute-file-chksum.py $REFDIR/*testnet.rawtx >/dev/null 2>&1")
T4=('test/test.py -On regtest')

[ -d .git -a -z "$NO_INSTALL"  -a -z "$TESTING" ] && {
	check
	(install)
	eval "cd .test-release/pydist/mmgen-*"
}
[ "$INSTALL_ONLY" ] && exit

function run_tests {
	for t in $1; do
		[ $t == 4 ] && LS=''
		eval "do_test \"\${T$t[@]}\""
	done
}

if [ "$*" ]; then
	run_tests "$*"
else
	echo 'Bitcoin and Bitcoin ABC must both be running for the following tests'
	echo 'The bitcoin-abc daemon must be listening on RPC port 8442 (-rpcport 8442)'
	echo -n 'Hit ENTER to continue: '; read
	run_tests '1'
	echo 'The bitcoin (mainnet) and testnet daemons must both be running for the following tests'
	echo -n 'Hit ENTER to continue: '; read
	run_tests '2 3'
	echo 'You may stop the mainnet and testnet daemons now'
	echo -n 'Hit ENTER to continue: '; read
	run_tests '4'
fi

echo -e "$LS${GREEN}All OK$RESET"
