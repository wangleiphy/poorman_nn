'''
Tests for MPS and MPO
'''
from numpy import *
from numpy.linalg import norm,svd
from copy import deepcopy
from numpy.testing import dec,assert_,assert_raises,assert_almost_equal,assert_allclose
from matplotlib.pyplot import *
import torch.nn.functional as F
from torch.nn import Conv1d,Conv2d
from torch import autograd
import torch
import sys,pdb,time
from os import path
from spconv import SPConv

def test_pbc_conv1d():
    N=100
    m=random.random([N,N])
    t0=time.time()
    extended_dims=((N/2,N/2),(0,N))
    padded_matrix,info=zero_padding(m,extended_dims=extended_dims)
    pbc_fill_padding(padded_matrix,info)
    t1=time.time()
    pmat=pbc_padding(m,extended_dims=extended_dims)
    t2=time.time()
    print 'Elapse -> ',t1-t0,t2-t1
    assert_allclose(padded_matrix,pmat)

def test_conv1d():
    #out_dims, in_dims, features.
    filters=autograd.Variable(torch.randn(33,16,3))
    #minibatch, in_dims, features.
    inputs = autograd.Variable(torch.randn(20, 16, 50))
    print F.conv1d(inputs,filters)
    pdb.set_trace()

def test_conv2d():
    ts=arange(16).reshape([1,4,4])
    #[ 0, 1, 2, 3]
    #[ 4, 5, 6, 7]
    #[ 8, 9,10,11]
    #[12,13,14,15]
    ts=autograd.Variable(1.0*torch.Tensor([ts,ts+1]))
    #2 features, kernel size 3x3
    cv=Conv2d(1,2,kernel_size=(3,3),stride=(1,1),padding=(0,0))
    cv.weight.data[...]=torch.Tensor([[[[1.,1,1],[1,0,1],[1,1,1.]]],[[[0,1,0],[1,0,1],[0,1,0]]]])
    cv.bias.data[...]=torch.Tensor([0,1])
    res=cv(ts)
    assert_allclose(res.data.numpy(),[[[[40,48],[72,80]],[[21,25],[37,41]]],[[[48,56],[80,88]],[[25,29],[41,45]]]])

    #new
    fltr=complex128([[[[1.,1,1],[1,0,1],[1,1,1.]]],[[[0,1,0],[1,0,1],[0,1,0]]]])
    sv=SPConv(fltr,bias=cv.bias.data.numpy(),img_in_shape=(4,4),dtype='float32',strides=(1,1),boundary='O')
    x=transpose(ts.data.numpy(),axes=(2,3,0,1))
    res2=sv.forward(complex128(ascontiguousarray(x)))
    res2=transpose(res2,axes=(2,3,0,1))
    assert_allclose(res2,[[[[40,48],[72,80]],[[21,25],[37,41]]],[[[48,56],[80,88]],[[25,29],[41,45]]]])
    pdb.set_trace()

def test_conv2d_per():
    num_batch=1
    dim_x=20
    dim_y=20
    K=3
    nfin=10
    nfout=16
    print "Testing forward"
    ts=random.random([num_batch,nfin,dim_x,dim_y])
    ts=autograd.Variable(torch.Tensor(ts),requires_grad=True)
    #2 features, kernel size 3x3
    cv=Conv2d(nfin,nfout,kernel_size=(K,K),stride=(1,1),padding=(0,0))
    fltr=cv.weight.data.numpy()
    sv=SPConv(float32(fltr),float32(cv.bias.data.numpy()),(dim_x,dim_y),strides=(1,1),boundary='O', w_contiguous=True)
    #xin_np=ascontiguousarray(transpose(ts.data.numpy(),(0,2,3,1)))
    #xin_np=ascontiguousarray(transpose(ts.data.numpy(),(2,3,0,1)))
    xin_np=ascontiguousarray(transpose(ts.data.numpy(),(2,3,1,0)))
    xin_np1=xin_np[...,0]
    ntest=5
    t0=time.time()
    for i in xrange(ntest):
        y1=cv(ts)
    t1=time.time()
    for i in xrange(ntest):
        y2=sv.forward(xin_np)
    t2=time.time()
    for i in xrange(ntest):
        y3=sv.forward(xin_np1)
    t3=time.time()
    print "Elapse old = %s, new = %s, new_1 = %s"%(t1-t0,t2-t1,t3-t2)
    res1=y1.data.numpy()
    #res2=transpose(y2,(2,3,0,1))
    #res2=transpose(y2,(0,3,1,2))
    res2=transpose(y2,(3,2,0,1))
    res3=transpose(y3[...,newaxis],(3,2,0,1))
    assert_allclose(res1,res2,atol=1e-4)
    assert_allclose(res1,res3,atol=1e-4)

    print "Testing backward"
    dy=torch.randn(*y1.size())
    dy_np=ascontiguousarray(transpose(dy.numpy(),(2,3,1,0)))
    dy_np1=dy_np[...,0]
    dweight=zeros_like(sv._fltr_flatten)
    dbias=zeros_like(sv.bias)
    dweight1=zeros_like(sv._fltr_flatten)
    dbias1=zeros_like(sv.bias)
    dx=zeros_like(xin_np)
    dx1=zeros_like(xin_np1)

    t0=time.time()
    y1.backward(dy)
    t1=time.time()
    for i in xrange(ntest):
        sv.backward(xin_np, y2, dy_np, dx, dweight, dbias, mask=(1,1,1))
    t2=time.time()
    for i in xrange(ntest):
        sv.backward(xin_np1, y3, dy_np1, dx1, dweight1, dbias1, mask=(1,1,1))
    t3=time.time()
    print "Elapse old = %s, new = %s, new-1 = %s"%(t1-t0,(t2-t1)/ntest,(t3-t2)/ntest)
    dweight/=ntest
    dx/=ntest
    dbias/=ntest
    dweight1/=ntest
    dx1/=ntest
    dbias1/=ntest

    #reshape back
    dx0=transpose(ts.grad.data.numpy(),(2,3,1,0))
    dx1=dx1[...,newaxis]

    wfactor=dweight.mean()
    bfactor=dbias.mean()
    dweight=reshape(dweight,cv.weight.size())/wfactor
    dweight1=reshape(dweight1,cv.weight.size())/wfactor
    assert_allclose(dx0,dx,atol=2e-3)
    assert_allclose(cv.weight.grad.data.numpy()/wfactor,dweight,atol=2e-3)
    assert_allclose(cv.bias.grad.data.numpy()/bfactor,dbias/bfactor,atol=2e-3)
    assert_allclose(dx0,dx1,atol=2e-3)
    assert_allclose(cv.weight.grad.data.numpy()/wfactor,dweight1,atol=2e-3)
    assert_allclose(cv.bias.grad.data.numpy()/bfactor,dbias1/bfactor,atol=2e-3)
    pdb.set_trace()

#test_pbc_conv1d()
#test_conv1d()
#test_conv2d()
test_conv2d_per()
