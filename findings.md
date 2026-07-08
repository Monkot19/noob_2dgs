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

## Fisheye Video Capture

- User captured a new 58-second fisheye-camera video at 10 Hz, producing about 580 frames, and uploaded the extracted images to the server dataset folder.
- Fisheye intrinsics can and should be used in COLMAP if calibration is available.
- The correct path is not to train 2DGS directly on a fisheye camera model. Instead:
  1. COLMAP feature extraction uses the fisheye model and known intrinsics.
  2. COLMAP estimates poses/sparse points.
  3. `image_undistorter` writes undistorted `images/` and `sparse/0/` with `PINHOLE` intrinsics.
  4. 2DGS trains on that undistorted COLMAP output.
- For OpenCV fisheye calibration, use COLMAP `OPENCV_FISHEYE` with parameter order:

```text
fx,fy,cx,cy,k1,k2,k3,k4
```

- Video frame sequences should prefer sequential matching over exhaustive matching to reduce compute and exploit temporal continuity.
- `convert.py` now supports:
  - `--camera_params`
  - `--matcher exhaustive|sequential`

Fisheye dataset `reception_hall_by_geoscanS2` COLMAP result:

```text
Cameras: 1
Images: 598
Registered images: 598
Points: 21822
Observations: 506302
Mean track length: 23.201448
Mean observations per image: 846.658863
Mean reprojection error: 1.064254px
```

Interpretation:

- Full registration is excellent.
- Mean track length is much stronger than the old `reception_hall_colmap` result (~23.2 vs ~6.9), meaning points are observed across many more frames.
- Points and observations are substantially higher than the old dataset.
- Reprojection error is slightly above 1 px and slightly worse than the old ~0.96 px, but still plausible for fisheye/video data after undistortion.
- This dataset is a strong candidate to replace the old 129-image dataset as the next 2DGS baseline.

Fisheye undistortion issue:

- User compared fisheye input frames with COLMAP undistorted output images.
- The input fisheye frames have a very wide field of view, but COLMAP's undistorted `images/` output is cropped to a very small central region.
- This can happen because `image_undistorter` converts the fisheye camera to a pinhole camera and, by default, tends to avoid large invalid/blank border regions.
- For 2DGS this is important: the model only consumes the undistorted pinhole `images/` and `sparse/0`, so an overly narrow undistortion output discards much of the useful fisheye coverage.
- Before training the 30k run, verify and tune the undistortion strategy so the resulting `images/` retain enough useful field of view.
- User already completed one 30k 2DGS training run on the narrow-FOV fisheye COLMAP output:
  - Dataset: `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2`
  - Output: `/root/autodl-tmp/outputs/reception_hall_geoscanS2_30k_v1`
  - Final train L1: `0.009084`
  - Final train PSNR: `37.131`
  - Points: `230465`
  - `render.py --skip_mesh` completed.
- This narrow-FOV run is useful as a baseline proving the fisheye COLMAP output can train, but it does not solve the scene-size problem because the undistorted images discarded too much field of view.
- User created a candidate wider-FOV undistortion output at `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_undistorter` using `colmap image_undistorter --blank_pixels 0.3 --max_image_size 1600`.
- Next training should use `_undistorter` only after visually checking that its `images/` retain significantly more scene coverage than the narrow original output.

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

Observed from the first user screenshots:

- Severe star-like streaks and stretched Gaussian splats.
- Large black/uncovered regions around the rendered scene.
- Walls and ceiling appear smeared into translucent sheets.
- The sign text is still partly visible, suggesting some high-frequency appearance remains, but geometry/visibility is unstable.

Interpretation:

- These first screenshots came from free-view movement in `2DGSmonitor`, not `render.py`.
- Free-view monitor artifacts are useful for judging view-space robustness, but they should not be treated as the primary train-view quality metric.
- The model should be evaluated first through GT/render pairs from training-camera renders.

Observed from GT/render pairs for `reception_hall_balanced_v1`:

- Camera alignment is broadly correct; the render sees the right wall/sign/plants/sofa/fire cabinet regions.
- The reconstruction is not fully collapsed, but it is heavily over-smoothed.
- Blue sign: text remains partly readable, but edges and sign boundaries are smeared.
- Wall/sofa: wall is very smooth and sheet-like; sofa loses material detail.
- Plants: global shape and color are acceptable, but leaf boundaries and fine structure are softened.
- Fire cabinet: small text and hard edges are almost lost; this is the clearest failure case for detail preservation.

Interpretation:

- `lambda_dist=50` is still too strong for this scene when detail preservation matters.
- `densify_grad_threshold=0.0003` is higher than the default `0.0002`, so it may suppress fine-detail Gaussian growth.
- Default `-r -1` downscales images wider than 1.6K, which can hurt small text; using `-r 1` is important for evaluating text-heavy regions.
- The next experiment should prioritize high-resolution, lower geometry regularization, and more permissive densification.
- User later clarified that from other free-view monitor angles, the wall is not merely smooth; it has visible protrusions and poor geometry.
- This means training-view GT/render pairs alone are insufficient for judging reconstruction quality.
- The target quality should include free-view/novel-view stability, wall flatness from oblique viewpoints, and absence of floating stretched splats.
- If free-view wall geometry remains poor across multiple parameter sets, a new photo capture is likely more valuable than continued parameter tweaking.

Capture-quality implications:

- Indoor scenes with large plain walls, glossy floors, LED light strips, black sofa, reflective glass, and thin plants are difficult for image-only COLMAP/2DGS.
- A successful reshoot should prioritize dense view coverage, oblique views of walls, loop closure, slower motion, less blur, exposure stability, and enough parallax.
- For the current `reception_hall`, the dataset has 129 registered images, which is enough to run but may be sparse for a small indoor scene with weak/repetitive texture and reflective surfaces.

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
