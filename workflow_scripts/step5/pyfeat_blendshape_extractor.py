import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np

logger = logging.getLogger(__name__)


class PyFeatBlendshapeExtractor:
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        use_gpu: bool = False,
    ):
        self._model_path = model_path or os.environ.get("STEP5_PYFEAT_MODEL_PATH")
        self._model = None
        self._blendshape_names = None
        self._use_gpu = use_gpu
        
        try:
            import torch
            self._torch = torch
        except ImportError:
            raise RuntimeError(
                "PyTorch is required for py-feat blendshape extraction. "
                "Install with: pip install torch"
            )

        if device:
            self._device = device
        else:
            if use_gpu and torch.cuda.is_available():
                self._device = "cuda"
            else:
                if use_gpu and not torch.cuda.is_available():
                    logger.warning("CUDA requested for py-feat but no GPU detected; falling back to CPU mode")
                self._device = "cpu"

        self._initialize_model()

    def _initialize_model(self):
        if not self._model_path:
            self._download_model()
        
        if not Path(self._model_path).exists():
            raise RuntimeError(f"py-feat model not found at: {self._model_path}")

        try:
            checkpoint = self._torch.load(
                self._model_path,
                map_location=self._device,
                weights_only=True,
            )

            if isinstance(checkpoint, dict) and "net" in checkpoint:
                state_dict = checkpoint["net"]
            else:
                state_dict = checkpoint

            self._model = self._create_model_architecture(state_dict)
            self._model.load_state_dict(state_dict)
            self._model.eval()
            self._model.to(self._device)
            
            self._blendshape_names = self._get_blendshape_names()
            
            logger.info(f"py-feat blendshape model loaded: {self._model_path}")
        except Exception as e:
            logger.error(f"Failed to load py-feat model: {e}")
            raise

    def _download_model(self):
        try:
            from huggingface_hub import hf_hub_download
            
            preferred_cache_dir = (
                Path(__file__).parent
                / "models"
                / "blendshapes"
                / "opencv"
                / "pyfeat_models"
            )
            legacy_cache_dir = Path(__file__).parent / "models" / "pyfeat"

            cache_dir = legacy_cache_dir if legacy_cache_dir.exists() else preferred_cache_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            self._model_path = hf_hub_download(
                repo_id="py-feat/mp_blendshapes",
                filename="face_blendshapes.pth",
                cache_dir=str(cache_dir),
            )
            logger.info(f"Downloaded py-feat model to: {self._model_path}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to download py-feat model from HuggingFace: {e}. "
                "Set STEP5_PYFEAT_MODEL_PATH manually or install: pip install huggingface_hub"
            )

    def _create_model_architecture(self, state_dict: Dict[str, Any]):
        torch = self._torch

        if isinstance(state_dict, dict) and any(k.startswith("mlpmixer_blocks.") for k in state_dict.keys()):

            class _ChannelLayerNormNoBias(torch.nn.Module):
                def __init__(self, channels: int, eps: float = 1e-5):
                    super().__init__()
                    self.weight = torch.nn.Parameter(torch.ones(channels))
                    self.eps = eps

                def forward(self, x):
                    mean = x.mean(dim=1, keepdim=True)
                    var = (x - mean).pow(2).mean(dim=1, keepdim=True)
                    x = (x - mean) / torch.sqrt(var + self.eps)
                    return x * self.weight.view(1, -1, 1, 1)

            class _MLPMixerBlock(torch.nn.Module):
                def __init__(
                    self,
                    tokens: int,
                    channels: int,
                    token_mlp_dim: int,
                    channel_mlp_dim: int,
                ):
                    super().__init__()
                    self.norm1 = _ChannelLayerNormNoBias(channels)
                    self.mlp_token_mixing = torch.nn.Sequential(
                        torch.nn.Conv2d(tokens, token_mlp_dim, kernel_size=1, bias=True),
                        torch.nn.GELU(),
                        torch.nn.Identity(),
                        torch.nn.Conv2d(token_mlp_dim, tokens, kernel_size=1, bias=True),
                    )
                    self.norm2 = _ChannelLayerNormNoBias(channels)
                    self.mlp_channel_mixing = torch.nn.Sequential(
                        torch.nn.Conv2d(channels, channel_mlp_dim, kernel_size=1, bias=True),
                        torch.nn.GELU(),
                        torch.nn.Identity(),
                        torch.nn.Conv2d(channel_mlp_dim, channels, kernel_size=1, bias=True),
                    )

                def forward(self, x):
                    y = self.norm1(x)
                    y = y.permute(0, 2, 1, 3)
                    y = self.mlp_token_mixing(y)
                    y = y.permute(0, 2, 1, 3)
                    x = x + y

                    y = self.norm2(x)
                    y = self.mlp_channel_mixing(y)
                    x = x + y
                    return x

            class MediaPipeBlendshapesMLPMixer(torch.nn.Module):
                def __init__(self, sd: Dict[str, Any]):
                    super().__init__()

                    conv1_w = sd["conv1.weight"]
                    conv2_w = sd["conv2.weight"]
                    out_w = sd["output_mlp.weight"]

                    tokens_without_extra = int(conv1_w.shape[0])
                    num_landmarks = int(conv1_w.shape[1])
                    num_blendshapes = int(out_w.shape[0])

                    tokens = tokens_without_extra + 1
                    channels = int(conv2_w.shape[0])
                    token_mlp_dim = int(sd["mlpmixer_blocks.0.mlp_token_mixing.0.weight"].shape[0])
                    channel_mlp_dim = int(sd["mlpmixer_blocks.0.mlp_channel_mixing.0.weight"].shape[0])
                    num_blocks = len({k.split(".")[1] for k in sd.keys() if k.startswith("mlpmixer_blocks.")})

                    self.num_landmarks = num_landmarks
                    self.num_blendshapes = num_blendshapes

                    self.conv1 = torch.nn.Conv2d(num_landmarks, tokens_without_extra, kernel_size=1, bias=True)
                    self.conv2 = torch.nn.Conv2d(2, channels, kernel_size=1, bias=True)
                    self.extra_token = torch.nn.Parameter(torch.zeros(1, channels, 1, 1))

                    self.mlpmixer_blocks = torch.nn.ModuleList(
                        [
                            _MLPMixerBlock(
                                tokens=tokens,
                                channels=channels,
                                token_mlp_dim=token_mlp_dim,
                                channel_mlp_dim=channel_mlp_dim,
                            )
                            for _ in range(int(num_blocks))
                        ]
                    )

                    self.output_mlp = torch.nn.Conv2d(channels, num_blendshapes, kernel_size=1, bias=True)
                    self.sigmoid = torch.nn.Sigmoid()

                def forward(self, landmarks_xy):
                    if landmarks_xy.ndim != 3:
                        raise ValueError(f"Expected landmarks_xy to have shape [B, N, 2], got {tuple(landmarks_xy.shape)}")

                    x = landmarks_xy.unsqueeze(-1)
                    x = self.conv1(x)
                    x = x.permute(0, 2, 1, 3)
                    x = self.conv2(x)

                    extra = self.extra_token.expand(x.shape[0], -1, -1, -1)
                    x = torch.cat([x, extra], dim=2)

                    for block in self.mlpmixer_blocks:
                        x = block(x)

                    x = self.output_mlp(x)
                    x = x[:, :, -1, 0]
                    x = self.sigmoid(x)
                    return x

            return MediaPipeBlendshapesMLPMixer(state_dict)

        class MediaPipeBlendshapesSimpleMLP(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.num_landmarks = 146
                self.num_blendshapes = 52

                self.fc1 = torch.nn.Linear(self.num_landmarks * 2, 256)
                self.bn1 = torch.nn.BatchNorm1d(256)
                self.fc2 = torch.nn.Linear(256, 256)
                self.bn2 = torch.nn.BatchNorm1d(256)
                self.fc3 = torch.nn.Linear(256, 128)
                self.bn3 = torch.nn.BatchNorm1d(128)
                self.fc4 = torch.nn.Linear(128, self.num_blendshapes)
                self.relu = torch.nn.ReLU()
                self.sigmoid = torch.nn.Sigmoid()

            def forward(self, x):
                x = x.view(x.size(0), -1)
                x = self.relu(self.bn1(self.fc1(x)))
                x = self.relu(self.bn2(self.fc2(x)))
                x = self.relu(self.bn3(self.fc3(x)))
                x = self.sigmoid(self.fc4(x))
                return x

        return MediaPipeBlendshapesSimpleMLP()

    def _get_blendshape_names(self) -> List[str]:
        return [
            "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft",
            "browOuterUpRight", "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
            "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
            "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
            "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
            "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen",
            "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
            "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthLeft",
            "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft",
            "mouthPressRight", "mouthPucker", "mouthRight", "mouthRollLower",
            "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft",
            "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
            "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight",
            "tongueOut"
        ]

    def _select_landmark_subset(self, landmarks_478: np.ndarray) -> np.ndarray:
        landmark_indices = [
            0, 1, 4, 5, 6, 7, 8, 10, 13, 14, 17, 21, 33, 37, 39, 40, 46, 52, 53, 54,
            55, 58, 61, 63, 65, 66, 67, 68, 69, 70, 78, 80, 81, 82, 84, 87, 88, 91,
            93, 95, 103, 105, 107, 109, 127, 132, 133, 136, 144, 145, 146, 148, 149,
            150, 152, 153, 154, 155, 157, 158, 159, 160, 161, 162, 163, 168, 172,
            173, 176, 178, 181, 185, 191, 195, 197, 234, 246, 249, 251, 263, 267,
            269, 270, 276, 282, 283, 284, 285, 288, 291, 293, 295, 296, 297, 298,
            299, 300, 308, 310, 311, 312, 314, 317, 318, 321, 323, 324, 332, 334,
            336, 338, 356, 361, 362, 365, 373, 374, 375, 377, 378, 379, 380, 381,
            382, 384, 385, 386, 387, 388, 389, 390, 397, 398, 402, 405, 415, 466,
            468, 469, 470, 471, 472, 473, 474, 475, 476
        ]
        expected = getattr(self._model, "num_landmarks", None)
        if isinstance(expected, int) and expected > 0 and len(landmark_indices) != expected:
            logger.warning(
                "py-feat landmark subset size mismatch (got %s, expected %s). Truncating indices.",
                len(landmark_indices),
                expected,
            )
            landmark_indices = landmark_indices[:expected]
        return landmarks_478[landmark_indices, :2]

    def extract_blendshapes(
        self,
        landmarks_478: np.ndarray,
        image_width: int,
        image_height: int
    ) -> Optional[Dict[str, float]]:
        if landmarks_478 is None or len(landmarks_478) < 478:
            return None

        try:
            landmarks_subset = self._select_landmark_subset(landmarks_478)
            
            # Optimize: check normalization before tensor creation
            max_coord = float(np.max(np.abs(landmarks_subset))) if landmarks_subset.size > 0 else 0.0
            if max_coord <= 2.0:
                # Apply scaling in numpy (faster than tensor ops)
                landmarks_subset = landmarks_subset * np.array([image_width, image_height], dtype=np.float32)
            
            # Single tensor creation with optimal dtype
            landmarks_tensor = self._torch.from_numpy(landmarks_subset.copy()).float().unsqueeze(0)
            landmarks_tensor = landmarks_tensor.to(self._device)

            with self._torch.no_grad():
                blendshapes_tensor = self._model(landmarks_tensor)

            blendshapes_array = blendshapes_tensor.squeeze(0).detach().cpu().numpy()
            
            return {
                name: float(value)
                for name, value in zip(self._blendshape_names, blendshapes_array)
            }
        except Exception as e:
            logger.warning(f"Failed to extract blendshapes: {e}")
            return None
