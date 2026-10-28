import torch
import torch.nn as nn
from harness import CHECKPOINT, IMAGENET_MEAN, IMAGENET_STD
from torchvision import models

# compatible w/ amd64 docker image
torch.backends.nnpack.set_flags(False)

ARCHITECTURES = {
    'mobilenet_v3_small': (
        models.mobilenet_v3_small,
        models.MobileNet_V3_Small_Weights.IMAGENET1K_V1,
    ),
    'mobilenet_v3_large': (
        models.mobilenet_v3_large,
        models.MobileNet_V3_Large_Weights.IMAGENET1K_V2,
    ),
}


def build_model(arch: str, num_classes: int, pretrained=False):
    factory, weights = ARCHITECTURES[arch]
    model = factory(weights=weights if pretrained else None)
    head = model.classifier[3]
    assert isinstance(head, nn.Linear)
    model.classifier[3] = nn.Linear(head.in_features, num_classes)
    return model


def load_checkpoint(path=CHECKPOINT):
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    model = build_model(checkpoint['arch'], len(checkpoint['classes']))
    model.load_state_dict(checkpoint['state_dict'])
    return model.eval(), checkpoint['classes'], checkpoint


class Deployable(nn.Module):
    """
    Takes RGB in [0,1] as NCHW (order of the dimensions in a batch of images held as a 4D tensor) and returns probabilities, so the device does no
    normalization and reads confidences straight from the output.
    """

    def __init__(self, net):
        super().__init__()
        self.net = net
        self.register_buffer('mean', torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor(IMAGENET_STD).view(1, 3, 1, 1))

    def forward(self, x):
        return torch.softmax(self.net((x - self.mean) / self.std), dim=1)


class NhwcDeployable(Deployable):
    """
    The TFLite input is NHWC - layout of an Android bitmap buffer.
    """

    def forward(self, x):
        return super().forward(x.permute(0, 3, 1, 2))
