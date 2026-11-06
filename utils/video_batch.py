"""Shared validation helpers for ComfyUI video IMAGE batches."""

import torch


def validate_video_batch(images: torch.Tensor, normalize: bool = True) -> torch.Tensor:
    """Validate a THWC RGB/RGBA batch and optionally clamp it to normalized range."""
    if not isinstance(images, torch.Tensor):
        raise TypeError("image must be a torch.Tensor batch in THWC layout.")
    if images.dim() != 4:
        raise ValueError(f"Expected image batch in THWC layout, got shape={tuple(images.shape)}")
    if images.size(0) < 1:
        raise ValueError("Silent film finish requires at least one frame.")
    if images.size(-1) not in (3, 4):
        raise ValueError(f"Expected 3 or 4 channels, got {images.size(-1)}.")
    images = images.detach()
    return images.float().clamp(0.0, 1.0) if normalize else images
