'''
Linear Layer.
'''

import numpy as np
import scipy.sparse as sps
import pdb

from core import Layer
from lib.linear import lib as flinear

__all__=['Linear', 'Apdot']

class Linear(Layer):
    '''
    Linear Layer.

    Attributes:
        :input_shape: two types allowed, (num_batch, weight.shape[1]), or (weight.shape[1],)
        :weight: 2darray, (fout, fin), in fortran order.
        :bias: 1darray, (fout,)
    '''
    def __init__(self, input_shape, dtype, weight, bias):
        self.weight = np.asfortranarray(weight, dtype=dtype)
        self.bias = np.asarray(bias,dtype=dtype)
        if input_shape[-1] != weight.shape[1]:
            raise ValueError('Shape Mismatch!')
        output_shape = input_shape[:-1]+(weight.shape[0],)
        super(Linear, self).__init__(input_shape, output_shape, dtype=dtype)

        if dtype=='complex128':
            dtype_token = 'z'
        elif dtype=='complex64':
            dtype_token = 'c'
        elif dtype=='float64':
            dtype_token = 'd'
        elif dtype=='float32':
            dtype_token = 's'
        else:
            raise TypeError("dtype error!")
        self._fforward=eval('flinear.forward_%s'%(dtype_token))
        self._fbackward=eval('flinear.backward_%s'%(dtype_token))
        #self._fforward1=eval('flinear.forward1_%s'%(dtype_token))
        #self._fbackward1=eval('flinear.backward1_%s'%(dtype_token))

    def __str__(self):
        return self.__repr__()+'\n  dtype = %s\n  weight => %s\n  bias => %s'%(self.dtype,self.weight.shape,self.bias.shape)

    def forward(self, x):
        y = self._fforward(np.atleast_2d(x), self.weight, self.bias)
        return y.reshape(self.output_shape, order='F')

    def backward(self, xy, dy, mask=(1,1)):
        x,y = xy
        dx, dweight, dbias = self._fbackward(np.atleast_2d(dy), np.atleast_2d(x), self.weight,
            do_xgrad=mask[1], do_wgrad=mask[0], do_bgrad=mask[0])
        return np.concatenate([dweight.ravel(order='F'), dbias]), dx.reshape(self.input_shape, order='F')

    def get_variables(self):
        return np.concatenate([self.weight.ravel(order='F'),self.bias])

    def set_variables(self, variables, mode='set'):
        w0=self.weight.copy()
        if mode=='set':
            weight0, bias0 =self.weight.copy(),self.bias.copy()
            np.copyto(self.weight,variables[:self.weight.size].reshape(self.weight.shape, order='F'))
            np.copyto(self.bias,variables[self.weight.size:].reshape(self.bias.shape, order='F'))
        elif mode=='add':
            self.weight+=variables[0]
            self.bias+=variables[1]

    @property
    def num_variables(self):
        return self.weight.size+self.bias.size

class Apdot(Linear):
    '''product layer.'''

    def __init__(self, input_shape, dtype, weight, bias):
        self.weight = np.asfortranarray(weight, dtype=dtype)
        self.bias = np.asarray(bias,dtype=dtype)
        if input_shape[-1] != weight.shape[1]:
            raise ValueError('Shape Mismatch!')
        output_shape = input_shape[:-1]+(weight.shape[0],)
        super(Linear, self).__init__(input_shape, output_shape, dtype=dtype)

    def forward(self, x):
        if x.ndim==1:
            x=x[np.newaxis]
        y=(np.prod(self.weight+x[:,np.newaxis,:],axis=2)*self.bias).reshape(self.output_shape, order='F')
        return y

    def backward(self, xy, dy, mask=(1,1)):
        x,y = xy
        if dy.ndim==1:
            dy=dy[np.newaxis]
            x=x[np.newaxis]
            y=y[np.newaxis]
        pmat=(dy*y)[:,:,np.newaxis]/(self.weight+x[:,np.newaxis,:])
        dweight=pmat.sum(axis=0)
        dx=pmat.sum(axis=1)
        dbias=((dy*y)/self.bias).sum(axis=0)
        return np.concatenate([dweight.ravel(order='F'), dbias]), dx.reshape(self.input_shape, order='F')

