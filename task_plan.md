# Task Plan

Last updated: 2026-07-07

## Goal

Maintain and improve this fork of 2D Gaussian Splatting for local editing plus AutoDL server execution.

The overall project goal is to convert data captured by a self-built handheld mapping device into high-quality 2DGS reconstructed scenes. The handheld device includes camera, LiDAR, synchronizer, industrial computer, and related acquisition hardware. The expected project pipeline is:

1. Deploy and run FastLIVO2 on the handheld device.
2. Capture synchronized image/LiDAR data with the device.
3. Transfer the captured data to the local/server workflow.
4. Run COLMAP or an equivalent pose/point-cloud preparation stage.
5. Train 2DGS.
6. Render 2DGS outputs and evaluate reconstructed scene quality.

The immediate technical goal is to obtain a cleaner reconstruction for `reception_hall`, especially reducing floating Gaussians and wall artifacts while preserving wall text/detail.

## Current Project State

- Local repository: `D:\workspace\2DGS`
- GitHub repository: `https://github.com/Monkot19/noob_2dgs.git`
- Upstream repository: `https://github.com/hbb1/2d-gaussian-splatting.git`
- Server repository path: `/root/autodl-tmp/noob_2dgs`
- Main dataset: `/root/autodl-tmp/datasets/reception_hall_colmap`
- Main output root: `/root/autodl-tmp/outputs`
- New capture: 58-second fisheye-camera video at 10 Hz, about 580 extracted frames uploaded under the AutoDL dataset folder.

## Operating Convention

- Use `planning-with-files` throughout this project.
- At the start of future project work, read `task_plan.md`, `findings.md`, and `progress.md` before making decisions.
- After new experiments, errors, code changes, or important conclusions, update the relevant planning files before finishing.
- Keep project memory in root-level planning files; keep `.codex/` as local Codex tooling unless intentionally shared.

## Completed

- Cloned upstream 2DGS into the local workspace.
- Initialized submodules:
  - `submodules/diff-surfel-rasterization`
  - `submodules/simple-knn`
  - `submodules/diff-surfel-rasterization/third_party/glm`
- Renamed original remote to `upstream`.
- Added user GitHub repository as `origin`.
- Pushed local fork to GitHub.
- Created documentation:
  - `docs/DEPLOYMENT_WORKFLOW.md`
  - `docs/2DGS_CHINESE_WORKFLOW.md`
- Extended `convert.py`:
  - Added `--camera_per_image` for mixed image dimensions.
  - Added Mapper fallback when `--Mapper.ba_global_function_tolerance=...` is unsupported by older COLMAP.
  - Added `--camera_params` for known COLMAP intrinsics.
  - Added `--matcher sequential` for video/frame-sequence datasets.
- AutoDL environment reached a runnable state:
  - PyTorch CUDA works.
  - `diff_surfel_rasterization` imports successfully.
  - `simple_knn` imports successfully.
- COLMAP conversion succeeded for `reception_hall_colmap`:
  - 129 registered images.
  - 9715 sparse points.
  - Mean track length about 6.9.
  - Mean reprojection error about 0.96 px.
- Rendering reached image/video export; missing `ffmpeg` was identified as the blocker for MP4 video writing.
- Expanded Chinese workflow documentation with train/render parameter guide and context migration instructions.
- Created and committed persistent planning files:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- Loaded the project-local `planning-with-files` skill and confirmed existing planning files are the active project memory.

## In Progress

- Tuning `train.py` parameters for `reception_hall_colmap`.
- Preparing a new fisheye-video dataset using known fisheye intrinsics in COLMAP.
- Balancing:
  - reducing floating colored Gaussians,
  - keeping walls flat,
  - preserving wall text and high-frequency visual details,
  - producing cleaner mesh output.
- Framing the broader handheld-device-to-2DGS pipeline, including whether FastLIVO2 outputs can eventually replace or reduce the COLMAP dependency.
- Diagnosing `reception_hall_balanced_v1`; GT/render pairs show broadly correct alignment but excessive smoothing and loss of small text/detail, while monitor/free-view inspection shows wall protrusions and poor novel-view geometry.

## Pipeline Directions

### Current Mainline: Images to COLMAP to 2DGS

Use this path as the stable baseline:

1. Device captures image sequence.
2. Images are organized into a 2DGS/COLMAP-compatible dataset.
3. COLMAP estimates camera poses and sparse points.
4. 2DGS trains from COLMAP output.
5. Rendering and mesh extraction evaluate final quality.

This path is already partially validated through `reception_hall_colmap`.

### Candidate Direction: FastLIVO2 to 2DGS Without COLMAP

Investigate whether FastLIVO2 can provide outputs that satisfy 2DGS training requirements directly or after conversion:

- camera poses/extrinsics per image,
- camera intrinsics,
- image timestamps and synchronization,
- sparse or dense colored point cloud,
- coordinate frame alignment between LiDAR, camera, and world.

This direction could reduce COLMAP cost/failure modes, especially for weak-texture indoor scenes, but it needs careful validation because 2DGS expects COLMAP-like camera models, poses, and scene normalization.

## Planned Experiments

### Balanced Indoor Scene

Use when floaters are improved but text/detail should remain readable.

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

### Detail-Preserving Indoor Scene

Use when wall text or small signs are blurred or become geometry protrusions.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_detail_r1 \
  -r 1 \
  --depth_ratio 0 \
  --lambda_normal 0.03 \
  --lambda_dist 10 \
  --opacity_cull 0.08 \
  --densify_grad_threshold 0.00025
```

### High-Resolution Low-Regularization Detail Test

Use when train-view renders are aligned but over-smoothed, especially for small text, sign edges, and thin plant structures.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_detail_v2 \
  -r 1 \
  --depth_ratio 0 \
  --lambda_normal 0.02 \
  --lambda_dist 5 \
  --opacity_cull 0.03 \
  --densify_grad_threshold 0.00015
```

### Strong Floater Cleanup

Use only when floaters dominate and texture detail is less important.

```bash
python train.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_clean_v2 \
  --depth_ratio 0 \
  --lambda_normal 0.1 \
  --lambda_dist 100 \
  --opacity_cull 0.1 \
  --densify_grad_threshold 0.0004 \
  --densify_until_iter 12000
```

## Render/Mesh Follow-Up

After each training run, render without mesh first:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/<run_name> \
  --skip_mesh
```

Then test unbounded mesh:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/<run_name> \
  --unbounded \
  --skip_train \
  --skip_test \
  --mesh_res 1024 \
  --num_cluster 20
```

## Risks

- Direct Gaussian point cloud visualization may look messy even when novel-view rendering is acceptable.
- Strong geometry regularization can convert high-frequency wall text into artificial protrusions.
- Lower regularization preserves texture but may reintroduce floaters.
- COLMAP quality is acceptable but sparse point count is not very high for an indoor scene; weak/repetitive texture may still hurt geometry.
- Current AutoDL system COLMAP may be `without CUDA` unless a custom COLMAP build is installed.
- `ffmpeg` may be missing on AutoDL, blocking MP4 creation from `render.py --render_path`.
- Local Windows environment is not the primary runtime; server Ubuntu is the preferred execution environment.

## Next Steps

1. Pull the latest repository state on AutoDL if needed:
   ```bash
   cd /root/autodl-tmp/noob_2dgs
   git pull --ff-only
   ```
2. Convert the new fisheye-video frame dataset using `OPENCV_FISHEYE`, known `camera_params`, and sequential matching.
3. Run `colmap model_analyzer` on the new dataset and compare against the old `reception_hall_colmap` stats.
4. Train a quick 2DGS smoke test on the new undistorted COLMAP output.
5. Compare the new run against `reception_hall_balanced_v1`:
   - blue sign text and edges,
   - fire cabinet text and box edges,
   - plant leaf boundaries,
   - wall smoothness,
   - amount of floaters in monitor/free-view inspection.
6. Record each experiment result in `progress.md`.
7. If a code-level improvement becomes necessary, implement locally, commit, push, then update the server with `git pull --ff-only`.
