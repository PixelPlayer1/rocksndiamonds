"""
File: BBBConv.py
Author: Jake Tuero (tuero@ualberta.ca)
Date: April 4, 2020
Description: Bayesian CNN Conv2D Implementation
Source: Taken from https://github.com/kumar-shridhar/PyTorch-BayesianCNN
"""

import torch
import torch.nn.functional as F
from torch.nn import Parameter

from metrics import calculate_kl as KL_DIV
from layers.misc import ModuleWrapper

import sys
sys.path.append("..")


class BBBConv2d(ModuleWrapper):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, dilation=1, bias=True, name='BBBLinear'):
        super(BBBConv2d, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = (kernel_size, kernel_size)
        self.stride = stride
        self.padding = padding
        self.dilation = dilation
        self.groups = 1
        self.use_bias = bias
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.name = name

        self.prior_mu = 0.0
        self.prior_sigma = 0.1

        self.W_mu = Parameter(torch.Tensor(out_channels, in_channels, *self.kernel_size))
        self.W_rho = Parameter(torch.Tensor(out_channels, in_channels, *self.kernel_size))

        self.bias_mu = Parameter(torch.Tensor(out_channels))
        self.bias_rho = Parameter(torch.Tensor(out_channels))
        # if self.use_bias:
        #     self.bias_mu = Parameter(torch.Tensor(out_channels))
        #     self.bias_rho = Parameter(torch.Tensor(out_channels))
        # else:
        #     self.register_parameter('bias_mu', None)
        #     self.register_parameter('bias_rho', None)

        self.reset_parameters()

    def reset_parameters(self):
        self.W_mu.data.normal_(0.0, 0.1)
        self.W_rho.data.normal_(-3.0, 0.1)

        self.bias_mu.data.normal_(0.0, 0.1)
        self.bias_rho.data.normal_(-3.0, 0.1)
        # if self.use_bias:
        #     self.bias_mu.data.normal_(0, 0.1)
        #     self.bias_rho.data.normal_(-3, 0.1)

    def forward(self, x):

        self.W_sigma = torch.log1p(torch.exp(self.W_rho))
        self.bias_sigma = torch.log1p(torch.exp(self.bias_rho))
        bias_var = self.bias_sigma ** 2
        # if self.use_bias:
        #     self.bias_sigma = torch.log1p(torch.exp(self.bias_rho))
        #     bias_var = self.bias_sigma ** 2
        # else:
        #     self.bias_sigma = bias_var = None

        act_mu = F.conv2d(x, self.W_mu, self.bias_mu, self.stride, self.padding, self.dilation, self.groups)
        act_var = 1e-16 + F.conv2d(x ** 2, self.W_sigma ** 2, bias_var, self.stride, self.padding, self.dilation, self.groups)
        act_std = torch.sqrt(act_var)

        eps = torch.empty(act_mu.size()).normal_(0.0, 1.0).to(self.device)
        return act_mu + act_std * eps
        # if self.training or sample:
        #     eps = torch.empty(act_mu.size()).normal_(0, 1).to(self.device)
        #     return act_mu + act_std * eps
        # else:
        #     return act_mu

    def kl_loss(self):
        kl = KL_DIV(self.prior_mu, self.prior_sigma, self.W_mu, self.W_sigma)
        kl += KL_DIV(self.prior_mu, self.prior_sigma, self.bias_mu, self.bias_sigma)
        # if self.use_bias:
        #     kl += KL_DIV(self.prior_mu, self.prior_sigma, self.bias_mu, self.bias_sigma)
        return kl
