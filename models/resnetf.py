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

"""ResNet in PyTorch.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Deep Residual Learning for Image Recognition. arXiv:1512.03385
"""

import torch.nn.functional as F
from torch import nn

from faultinjection_ops import zs_faultinjection_ops
from quantized_ops import zs_quantized_ops

conv_clamp_val = 0.05
fc_clamp_val = 0.1


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(
        self,
        in_planes,
        planes,
        stride,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    ):
        super(BasicBlock, self).__init__()
        if "conv" in faulty_layers:
            self.conv1 = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                in_planes,
                planes,
                kernel_size=3,
                stride=stride,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.conv1 = zs_quantized_ops.nnConv2dSymQuant_op(
                in_planes,
                planes,
                kernel_size=3,
                stride=stride,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
            )
        self.bn1 = nn.BatchNorm2d(planes)
        if "conv" in faulty_layers:
            self.conv2 = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                planes,
                planes,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.conv2 = zs_quantized_ops.nnConv2dSymQuant_op(
                planes,
                planes,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
            )
        self.bn2 = nn.BatchNorm2d(planes)
        self.relu1 = nn.ReLU()
        self.relu2 = nn.ReLU()
        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            if "conv" in faulty_layers:
                self.shortcut = nn.Sequential(
                    zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                        in_planes,
                        self.expansion * planes,
                        kernel_size=1,
                        stride=stride,
                        padding=0,
                        bias=False,
                        precision=precision,
                        clamp_val=conv_clamp_val,
                        BitErrorMap0to1=BitErrorMap0to1,
                        BitErrorMap1to0=BitErrorMap1to0,
                    ),
                    nn.BatchNorm2d(self.expansion * planes),
                )
            else:
                self.shortcut = nn.Sequential(
                    zs_quantized_ops.nnConv2dSymQuant_op(
                        in_planes,
                        self.expansion * planes,
                        kernel_size=1,
                        stride=stride,
                        padding=0,
                        bias=False,
                        precision=precision,
                        clamp_val=conv_clamp_val,
                    ),
                    nn.BatchNorm2d(self.expansion * planes),
                )

    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = self.relu2(out)
        return out


class ResNet(nn.Module):
    def __init__(
        self,
        block,
        num_blocks,
        num_classes,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    ):
        super(ResNet, self).__init__()
        self.in_planes = 64

        if "conv" in faulty_layers:
            self.conv1 = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                3,
                64,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.conv1 = zs_quantized_ops.nnConv2dSymQuant_op(
                3,
                64,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=False,
                precision=precision,
                clamp_val=conv_clamp_val,
            )
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(
            block,
            64,
            num_blocks[0],
            stride=1,
            precision=precision,
            ber=ber,
            position=position,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
            faulty_layers=faulty_layers,
        )
        self.layer2 = self._make_layer(
            block,
            128,
            num_blocks[1],
            stride=2,
            precision=precision,
            ber=ber,
            position=position,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
            faulty_layers=faulty_layers,
        )
        self.layer3 = self._make_layer(
            block,
            256,
            num_blocks[2],
            stride=2,
            precision=precision,
            ber=ber,
            position=position,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
            faulty_layers=faulty_layers,
        )
        self.layer4 = self._make_layer(
            block,
            512,
            num_blocks[3],
            stride=2,
            precision=precision,
            ber=ber,
            position=position,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
            faulty_layers=faulty_layers,
        )
        if "linear" in faulty_layers:
            self.linear = zs_faultinjection_ops.nnLinearPerturbWeight_op(
                512 * block.expansion,
                num_classes,
                precision,
                fc_clamp_val,
                BitErrorMap0to1=BitErrorMap0to1,
                BitErrorMap1to0=BitErrorMap1to0,
            )
        else:
            self.linear = zs_quantized_ops.nnLinearSymQuant_op(
                512 * block.expansion, num_classes, precision, fc_clamp_val
            )

    def _make_layer(
        self,
        block,
        planes,
        num_blocks,
        stride,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    ):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(
                block(
                    self.in_planes,
                    planes,
                    stride,
                    precision,
                    ber,
                    position,
                    BitErrorMap0to1,
                    BitErrorMap1to0,
                    faulty_layers,
                )
            )
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = F.avg_pool2d(out, 4)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def ResNet18(
    classes,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    return ResNet(
        BasicBlock,
        [2, 2, 2, 2],
        classes,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    )


def ResNet34(
    classes,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    return ResNet(
        BasicBlock,
        [3, 4, 6, 3],
        classes,
        precision,
        ber,
        position,
        BitErrorMap0to1,
        BitErrorMap1to0,
        faulty_layers,
    )


def resnetf(
    arch,
    classes,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    if arch == "resnet18":
        return ResNet18(
            classes,
            precision,
            ber,
            position,
            BitErrorMap0to1,
            BitErrorMap1to0,
            faulty_layers,
        )
    else:
        return ResNet34(
            classes,
            precision,
            ber,
            position,
            BitErrorMap0to1,
            BitErrorMap1to0,
            faulty_layers,
        )


# def test():
#    net = ResNet18()
#    y = net(torch.randn(1,3,32,32))
#    print(y.size())

# test()
