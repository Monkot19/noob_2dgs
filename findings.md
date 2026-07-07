# Findings

Last updated: 2026-07-07

## Repository and Workflow

- This repository is a fork-like working copy of `hbb1/2d-gaussian-splatting`.
- `origin` points to `https://github.com/Monkot19/noob_2dgs.git`.
- `upstream` points to `https://github.com/hbb1/2d-gaussian-splatting.git`.
- The intended workflow is:
  1. Modify locally.
  2. Commit and push to GitHub.
  3. Pull on AutoDL server.
  4. Run training/rendering on AutoDL.
- Project-local planning skill is installed at `.codex/skills/planning-with-files/`.
- Persistent planning files are stored in the project root, not in the skill directory.
- `.codex/` is local Codex tooling/configuration and should remain untracked unless there is a deliberate reason to share it.

## Local Environment

- Local Windows machine has an NVIDIA GPU, but the local CUDA/PyTorch environment was not made the primary runtime.
- Local setup hit PyTorch/CUDA DLL issues and missing `nvcc` in PATH.
- Ubuntu server execution is preferred.

## AutoDL Environment

- AutoDL base environment successfully imported:
  - `torch`
  - `diff_surfel_rasterization`
  - `simple_knn`
- `open3d` import initially failed through `dash/comm`; downgrading or pinning `dash`/`comm` is the known fix:

```bash
pip install "dash==2.14.2" "comm==0.1.4"
```

- `ffmpeg` may be missing, causing `mediapy` MP4 creation to fail:

```bash
apt update
apt install -y ffmpeg
```

## COLMAP

- System COLMAP observed on AutoDL:

```text
/usr/bin/colmap
COLMAP 3.6 ... without CUDA
```

- That build cannot use GPU SIFT.
- CPU COLMAP feature extraction can be killed due to memory pressure on larger images.
- A custom COLMAP 3.9.1 build with CUDA is the preferred GPU path if GPU COLMAP is required.
- For RTX 3090, compile with:

```bash
-DCMAKE_CUDA_ARCHITECTURES=86
```

- For RTX 4090, compile with:

```bash
-DCMAKE_CUDA_ARCHITECTURES=89
```

## Dataset: reception_hall_colmap

COLMAP model analyzer output:

```text
Cameras: 1
Images: 129
Registered images: 129
Points: 9715
Observations: 67185
Mean track length: 6.915594
Mean observations per image: 520.813953
Mean reprojection error: 0.959117px
```

Interpretation:

- Registration is good.
- Mean reprojection error below 1 px is acceptable.
- Sparse point count is moderate; indoor wall/texture quality may still limit geometry.
- Current artifacts are likely training/regularization/scene-texture tradeoffs rather than complete COLMAP failure.

## Training Observations

Default training:

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_geom
```

Observed issue:

- Many floating colored Gaussians.
- Space looks visually cluttered in point/Gaussian visualization.

Stronger cleanup run:

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_clean_v1 \
  --depth_ratio 0 \
  --lambda_normal 0.1 \
  --lambda_dist 100 \
  --opacity_cull 0.1 \
  --densify_grad_threshold 0.0004
```

Observed improvement:

- Floaters reduced.
- Walls became smoother.

Observed regression:

- Wall text/detail became less readable.
- Some wall text appeared as abnormal protrusions.

Interpretation:

- `lambda_normal=0.1` and `lambda_dist=100` may be too strong for text-bearing walls.
- High-frequency texture may be interpreted as geometry when regularization is too strong or resolution is too low.
- A balanced run should lower geometry regularization and slightly relax densification pruning.

## Key Parameter Effects

- `--lambda_dist`: reduces depth spread and floaters; too high can blur details or create geometry artifacts.
- `--lambda_normal`: smooths surfaces; too high can erase small text/texture.
- `--opacity_cull`: prunes weak Gaussians; too high can remove fine details.
- `--densify_grad_threshold`: higher means fewer new Gaussians; too high reduces detail.
- `-r 1`: preserves image detail; useful for wall text but costs more VRAM/time.
- `--depth_ratio 0`: preferred for indoor halls and large depth variation.
- `--depth_ratio 1`: better for bounded object-centric scenes.

## Documentation Notes

- `docs/2DGS_CHINESE_WORKFLOW.md` is the primary project guide.
- PowerShell may display Chinese Markdown as mojibake, but the file content is UTF-8 and renders correctly in normal Markdown viewers/GitHub.

## Context Migration

- If the conversation context is exhausted, start a new thread with:
  - GitHub repo URL.
  - Local path.
  - AutoDL path.
  - Dataset path.
  - Current output directory.
  - Latest command/error.
  - A request to read `docs/2DGS_CHINESE_WORKFLOW.md`, `task_plan.md`, `findings.md`, and `progress.md`.
