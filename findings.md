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

## Project Scope

- The user's broader project is a handheld-device-to-2DGS reconstruction pipeline.
- The handheld device is self-assembled and includes camera, LiDAR, synchronizer, industrial computer, and related acquisition components.
- FastLIVO2 is planned for deployment on the handheld device.
- The user's core responsibility is downstream data handling and reconstruction:
  - obtain captured data,
  - run COLMAP or an equivalent preparation stage,
  - train 2DGS,
  - render/evaluate reconstructed 2DGS scenes.
- A successful project means converting data from the handheld device into high-quality 2DGS reconstructed scenes.
- Possible future direction: use FastLIVO2 outputs to skip COLMAP if they can provide 2DGS-compatible camera poses, intrinsics, and point cloud data.

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

## FastLIVO2 as a Possible COLMAP Alternative

- Treat FastLIVO2-to-2DGS as a research/engineering branch, not yet the default path.
- Key validation questions:
  - Can FastLIVO2 output per-image camera poses in a stable world frame?
  - Are camera intrinsics and distortion parameters available in a form convertible to COLMAP/2DGS?
  - Are image timestamps matched cleanly to LiDAR/IMU poses?
  - Is the point cloud coordinate frame compatible with the camera poses?
  - Does 2DGS need a COLMAP-format `sparse/0` directory, or can we write a converter to produce equivalent `cameras`, `images`, and `points3D` files?
- Potential benefit:
  - Lower dependence on image-only feature matching, which can struggle on weak/repetitive indoor walls.
- Potential risk:
  - Pose/frame convention mistakes can create worse artifacts than COLMAP, even if the LiDAR SLAM trajectory itself looks good.

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

Balanced run:

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --depth_ratio 0 \
  --lambda_normal 0.05 \
  --lambda_dist 50 \
  --opacity_cull 0.08 \
  --densify_grad_threshold 0.0003
```

Observed from user screenshots:

- Severe star-like streaks and stretched Gaussian splats.
- Large black/uncovered regions around the rendered scene.
- Walls and ceiling appear smeared into translucent sheets.
- The sign text is still partly visible, suggesting some high-frequency appearance remains, but geometry/visibility is unstable.

Interpretation:

- First distinguish whether this is a bad model or a bad/free trajectory render.
- If training-camera renders are acceptable but `--render_path` is bad, the path likely leaves the observed camera manifold or sees unobserved regions.
- If training-camera renders are also bad, the problem is more likely training/data/COLMAP quality, scene normalization, or overly unstable Gaussian growth.
- Do not continue tuning mesh parameters until plain train-view renders are inspected.

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
