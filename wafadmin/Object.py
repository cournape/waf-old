
import warnings
warnings.warn("The WAF module Object has been renamed to TaskGen", DeprecationWarning, stacklevel=2)
del warnings

from TaskGen import *
