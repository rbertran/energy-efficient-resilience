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

# Adapted vgg16 from pytorch repo to include my
# fault injection operators and for cifar10

import torch
from torch import nn

from faultinjection_ops import zs_faultinjection_ops
from quantized_ops import zs_quantized_ops

# Per layer clamping currently based on manual values set
weight_clamp_values = [
    0.2,
    0.2,
    0.15,
    0.13,
    0.1,
    0.1,
    0.1,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
    0.05,
]
fc_weight_clamp = 0.1


class VGG(nn.Module):
    def __init__(self, features, classifier, classes=10, init_weights=True):
        super(VGG, self).__init__()
        self.features = features
        # self.avgpool = nn.AdaptiveAvgPool2d((7, 7))
        self.avgpool = nn.AvgPool2d(kernel_size=1, stride=1)
        self.classifier = classifier
        # self.classifier = nn.Sequential(
        #     nn.Linear(512 * 7 * 7, 4096),
        #     nn.ReLU(True),
        #     nn.Dropout(),
        #     nn.Linear(4096, 4096),
        #     nn.ReLU(True),
        #     nn.Dropout(),
        #     nn.Linear(4096, classes),
        # )
        if init_weights:
            self._initialize_weights()

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(
                    m.weight, mode="fan_out", nonlinearity="relu"
                )
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)


def make_classifier(
    classes,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    if "linear" in faulty_layers:
        classifier = zs_faultinjection_ops.nnLinearPerturbWeight_op(
            512,
            classes,
            precision,
            fc_weight_clamp,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
        )
    else:
        classifier = zs_quantized_ops.nnLinearSymQuant_op(
            512, classes, precision, fc_weight_clamp
        )

    return classifier


def make_layers(
    cfg,
    in_channels,
    batch_norm,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    layers = []
    # in_channels = 3
    cl = 0
    # pdb.set_trace()
    for v in cfg:
        if v == "M":
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
        else:
            if "conv" in faulty_layers:
                conv2d = zs_faultinjection_ops.nnConv2dPerturbWeight_op(
                    in_channels,
                    v,
                    kernel_size=3,
                    stride=1,
                    padding=1,
                    bias=True,
                    precision=precision,
                    clamp_val=weight_clamp_values[cl],
                    BitErrorMap0to1=BitErrorMap0to1,
                    BitErrorMap1to0=BitErrorMap1to0,
                )
            else:
                conv2d = zs_quantized_ops.nnConv2dSymQuant_op(
                    in_channels,
                    v,
                    kernel_size=3,
                    stride=1,
                    padding=1,
                    bias=True,
                    precision=precision,
                    clamp_val=weight_clamp_values[cl],
                )
            cl = cl + 1

            if batch_norm:
                layers += [conv2d, nn.BatchNorm2d(v), nn.ReLU(inplace=True)]
            else:
                layers += [conv2d, nn.ReLU(inplace=True)]
            in_channels = v
    return nn.Sequential(*layers)


cfgs = {
    "A": [64, "M", 128, "M", 256, 256, "M", 512, 512, "M", 512, 512, "M"],
    "B": [
        64,
        64,
        "M",
        128,
        128,
        "M",
        256,
        256,
        "M",
        512,
        512,
        "M",
        512,
        512,
        "M",
    ],
    "D": [
        64,
        64,
        "M",
        128,
        128,
        "M",
        256,
        256,
        256,
        "M",
        512,
        512,
        512,
        "M",
        512,
        512,
        512,
        "M",
    ],
    "E": [
        64,
        64,
        "M",
        128,
        128,
        "M",
        256,
        256,
        256,
        256,
        "M",
        512,
        512,
        512,
        512,
        "M",
        512,
        512,
        512,
        512,
        "M",
    ],
}


# def vgg(cfg,batch_norm,**kwargs):
#    kwargs['num_classes'] = 10
#    model = VGG(make_layers(cfgs[cfg], batch_norm=batch_norm), **kwargs)
#    return model


def vggf(
    cfg,
    input_channels,
    classes,
    batch_norm,
    precision,
    ber,
    position,
    BitErrorMap0to1,
    BitErrorMap1to0,
    faulty_layers,
):
    model = VGG(
        make_layers(
            cfgs[cfg],
            in_channels=input_channels,
            batch_norm=batch_norm,
            precision=precision,
            ber=ber,
            position=position,
            BitErrorMap0to1=BitErrorMap0to1,
            BitErrorMap1to0=BitErrorMap1to0,
            faulty_layers=faulty_layers,
        ),
        make_classifier(
            classes,
            precision,
            ber,
            position,
            BitErrorMap0to1,
            BitErrorMap1to0,
            faulty_layers,
        ),
        classes,
        True,
    )
    return model


# def _vgg(arch, cfg, batch_norm, pretrained, progress, **kwargs):
#    if pretrained:
#        kwargs['init_weights'] = False
#    model = VGG(make_layers(cfgs[cfg], batch_norm=batch_norm), **kwargs)
#    if pretrained:
#        state_dict = load_state_dict_from_url(model_urls[arch],
#                                              progress=progress)
#        model.load_state_dict(state_dict)
#    return model
#

# def vgg11(pretrained=False, progress=True, **kwargs):
#    r"""VGG 11-layer model (configuration "A") from
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg11', 'A', False, pretrained, progress, **kwargs)
#
#
# def vgg11_bn(pretrained=False, progress=True, **kwargs):
#    r"""VGG 11-layer model (configuration "A") with batch normalization
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg11_bn', 'A', True, pretrained, progress, **kwargs)
#
#
# def vgg13(pretrained=False, progress=True, **kwargs):
#    r"""VGG 13-layer model (configuration "B")
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg13', 'B', False, pretrained, progress, **kwargs)
#
#
# def vgg13_bn(pretrained=False, progress=True, **kwargs):
#    r"""VGG 13-layer model (configuration "B") with batch normalization
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg13_bn', 'B', True, pretrained, progress, **kwargs)
#
#
# def vgg16(pretrained=False, progress=True, **kwargs):
#    r"""VGG 16-layer model (configuration "D")
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg16', 'D', False, pretrained, progress, **kwargs)
#
#
# def vgg16_bn(pretrained=False, progress=True, **kwargs):
#    r"""VGG 16-layer model (configuration "D") with batch normalization
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg16_bn', 'D', True, pretrained, progress, **kwargs)
#
#
# def vgg19(pretrained=False, progress=True, **kwargs):
#    r"""VGG 19-layer model (configuration "E")
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg19', 'E', False, pretrained, progress, **kwargs)
#
#
# def vgg19_bn(pretrained=False, progress=True, **kwargs):
#    r"""VGG 19-layer model (configuration 'E') with batch normalization
#    `"Very Deep Convolutional Networks For Large-Scale Image
#    Recognition" <https://arxiv.org/pdf/1409.1556.pdf>`_
#    Args:
#        pretrained (bool): If True, returns a model pre-trained on ImageNet
#        progress (bool): If True, displays a progress bar of the download to
#        stderr
#    """
#    return _vgg('vgg19_bn', 'E', True, pretrained, progress, **kwargs)
#
