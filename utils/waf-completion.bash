#
# bash completion support for waf.
#
# To activate completion:
#
#    1) Copy this file to somewhere (e.g. ~/.waf-completion.sh).
#    2) Added the following line to your .bashrc:
#        source ~/.waf-completion.sh

__get_waf()
{
	# if the waf used contains a path component, check that it exists
	# otherwise, check that it is in the path with 'which'
	if [[ "$@" =~ "/" ]] && test -e "$@" ; then
		# check path?
		echo "$@"
	else
		which "$@"
	fi
}

_waf ()
{
	local cur cmds opts use
	# eval expands ~ and $VARS that may be in the waf program name.
	# Otherwise ~/$MYWAF/waf would not complete.
	local waf=$(eval __get_waf "${COMP_WORDS[0]}")
	COMPREPLY=()
	if test -z "$waf" ; then
		return
	fi
	cur=${COMP_WORDS[COMP_CWORD]}
	cmds=$("$waf" --help | grep '^\* Main commands:' |  cut -d: -f2- )
	opts=$("$waf" --help | grep '^[[:blank:]]*-' |  awk '
	{ for (i = 1; i <= NF; ++i) {
		if (($i ~ /^-/) && ($i !~ /:$/) && ($i !~ /---/)) {
			gsub("(,|=.*)","",$i); print $i;
		}
	}}')
	case "${cur}" in
		-*) use=$opts ;;
		*)  use=$cmds ;;
	esac
	COMPREPLY=( $( compgen -W "$use" -- $cur ) )
}

complete -o default -o nospace -F _waf waf
complete -o default -o nospace -F _waf waf-light
