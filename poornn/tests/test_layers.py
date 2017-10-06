from numpy import *
from numpy.testing import dec,assert_,assert_raises,assert_almost_equal,assert_allclose
import pdb,time

from ..layers import *
from ..checks import check_numdiff
from ..utils import typed_randn

def test_poly():
    kernels = ['polynomial','chebyshev', 'legendre','laguerre','hermite','hermiteE']
    for factorial_rescale in [True,False]:
        for kernel in kernels:
            func=Poly(input_shape=(-1,2), itype='complex128',params=[3.,2,2+1j], kernel=kernel, factorial_rescale = factorial_rescale)
            print('Test numdiff for \n%s.'%func)
            assert_(all(check_numdiff(func)))

def test_mobiusgeo():
    func1=Mobius(input_shape=(-1,2), itype='complex128',params=[1,2j,1e10], var_mask=[1,1,0])
    func2 = Georgiou1992(input_shape=(-1,2), itype='complex128',params=[1,2.], var_mask=[1,1])
    for func in [func1, func2]:
        print('Test numdiff for \n%s.'%func)
        assert_(all(check_numdiff(func)))

def test_all():
    random.seed(3)
    test_poly()
    test_mobiusgeo()

if __name__=='__main__':
    test_all()
