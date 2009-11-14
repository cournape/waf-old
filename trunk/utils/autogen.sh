#! /bin/sh

# This script is an autogen.sh-like wrapper for allowing WAF to be installed by jhbuild

WAF=./waf-light
prefix=""

while test -n "$1"; do
	case $1 in
		--prefix=*)
			prefix="$1"
			;;
		--prefix)
			shift;
			prefix="--prefix=$1"
			;;
	esac
	shift;
done


cat > Makefile << EOF
#!/usr/bin/make -f

all:

all_debug:

all_progress:

install:
	$WAF install --yes --strip $prefix

uninstall:
	$WAF uninstall

clean:
	$WAF clean

distclean:
	$WAF distclean
	-rm -f Makefile

check:

dist:

EOF

