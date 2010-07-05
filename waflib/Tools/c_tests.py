#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
configuration tests...
"""

from Configure import conf

INLINE_CODE = '''
typedef int foo_t;
static %s foo_t static_foo () {return 0; }
%s foo_t foo () {
	return 0;
}
'''
INLINE_VALUES = ['inline', '__inline__', '__inline']

@conf
def check_inline(self, **kw):
	'''
	check for the right value for inline
	define INLINE_MACRO to 1 if the define is found
	if the inline macro is not 'inline', add a define for the config.h (#define inline __inline__)
	'''

	self.start_msg('Checking for inline')

	if not 'define_name' in kw:
		kw['define_name'] = 'INLINE_MACRO'
	if not 'features' in kw:
		if self.env.CXX:
			kw['features'] = ['cxx']
		else:
			kw['features'] = ['cc']
	kw['mandatory'] = True

	for x in INLINE_VALUES:
		kw['fragment'] = INLINE_CODE % (x, x)

		try:
			self.check_cc(**kw)
		except self.errors.ConfigurationError:
			continue
		else:
			self.end_msg(x)
			if x != 'inline':
				self.define('inline', i, quote=False)
			return x
	raise self.errors.ConfigurationError('could not use inline functions')

