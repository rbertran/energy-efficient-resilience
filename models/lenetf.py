# Copyright 2022 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import torch.nn.functional as F
from torch import nn

from faultinjection_ops import zs_faultinjection_ops
from quantized_ops import zs_quantized_ops

conv_clamp_val = 0.1
fc_clamp_val = 0.1


class LeNet(nn.Module):
    def __init__(
        self,
        input_channels,
        classes,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    ):
        super(LeNet, self).__init__()
        if "conv" in faulty_layers:
            self.conv1 = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                input_channels,
                32,
                kernel_size=3,
                stride=1,
                padding=0,
                bias=True,
                precision=precision,
                clamp_val=conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
            self.conv2 = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                32,
                64,
                kernel_size=3,
                stride=1,
                padding=0,
                bias=True,
                precision=precision,
                clamp_val=conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.conv1 = zs_quantized_ops.nnConv2dSymQuant_op(
                input_channels,
                32,
                kernel_size=3,
                stride=1,
                padding=0,
                bias=True,
                precision=precision,
                clamp_val=conv_clamp_val,
            )
            self.conv2 = zs_quantized_ops.nnConv2dSymQuant_op(
                32,
                64,
                kernel_size=3,
                stride=1,
                padding=0,
                bias=True,
                precision=precision,
                clamp_val=conv_clamp_val,
            )
        if "linear" in faulty_layers:
            self.fc1 = zs_faultinjection_ops.nnLinearPerturbWeight_op(
                9216,
                128,
                precision,
                fc_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
            self.fc2 = zs_faultinjection_ops.nnLinearPerturbWeight_op(
                128,
                classes,
                precision,
                conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.fc1 = zs_quantized_ops.nnLinearSymQuant_op(
                9216, 128, precision, fc_clamp_val
            )
            self.fc2 = zs_quantized_ops.nnLinearSymQuant_op(
                128, classes, precision, conv_clamp_val
            )
        self.dropout1 = nn.Dropout2d(0.25)
        self.dropout2 = nn.Dropout2d(0.5)
        self.relu1 = nn.ReLU(True)
        self.relu2 = nn.ReLU(True)
        self.relu3 = nn.ReLU(True)

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu1(x)
        x = self.conv2(x)
        x = self.relu2(x)
        x = F.max_pool2d(x, 2)
        # x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = self.relu3(x)
        # x = self.dropout2(x)
        output = self.fc2(x)
        # output = F.log_softmax(x, dim=1)
        return output


def lenetf(
    input_channels,
    classes,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    model = LeNet(
        input_channels,
        classes,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    )
    return model
