# A filter for the d comments
# it is much slower than the non-regexp one

txt = r"""(\/\+)|(\+\/)|/\*[^*]*\*+([^/*][^*]*\*+)*/|//[^\n]*|("(\\.|[^"\\])*"|'(\\.|[^'\\])*'|.[^\+/'"]*)"""
re_outer = re.compile(txt, re.M | re.S)
re_inner = re.compile(r"""(/\+)|(\+/)|.+?(?=/\+|\+/)""", re.M | re.S)

def filter(txt):
	idx = 0
	incomment = 0
	buf = []
	length = len(txt)
	while idx < length:
		if 0 == incomment:
			m = re_outer.match(txt, idx)
			idx += len(m.group(0))
			if m.group(1):
				incomment = 1
			elif m.group(2):
				raise "bug!"
			else:
				buf.append(m.group(0))
		else:
			m = re_inner.match(txt, idx)
			if m.group(1):
				idx += 2
				incomment += 1
			elif m.group(2):
				idx += 2
				incomment -= 1
			else:
				idx += len(m.group(0))
	return "".join(buf)
