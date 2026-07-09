# Progress

Last updated: 2026-07-09

## Current Status

The project is operational on AutoDL. The current focus is experiment management and reconstruction-quality tuning for `reception_hall_colmap`.

## Timeline

### 2026-07-02

- Cloned upstream 2DGS into `D:\workspace\2DGS`.
- Initialized submodules.
- Created GitHub repository `Monkot19/noob_2dgs`.
- Pushed local repository to GitHub.
- Created deployment workflow documentation.
- Attempted local Windows environment setup; local runtime was deprioritized due PyTorch/CUDA issues.

### 2026-07-06

- Deployed repository on AutoDL.
- Confirmed server CUDA/PyTorch and CUDA extensions work.
- Handled COLMAP conversion issues:
  - Qt display failure.
  - OpenGL context failure.
  - CPU feature extraction memory pressure.
  - System COLMAP without CUDA.
  - Mixed image dimensions.
- Modified `convert.py` for:
  - `--camera_per_image`
  - Mapper compatibility fallback
- Converted `reception_hall_colmap` successfully.
- Trained initial models.
- Rendered outputs and found `ffmpeg` missing for video writing.
- Created and expanded Chinese workflow documentation.

### 2026-07-07

- Expanded `docs/2DGS_CHINESE_WORKFLOW.md` with:
  - detailed `train.py` parameters,
  - detailed `render.py` parameters,
  - typical scene presets,
  - artifact-to-parameter troubleshooting,
  - context migration notes.
- Created this planning-file set:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- Explicitly loaded the project-local `planning-with-files` skill from `.codex/skills/planning-with-files/SKILL.md`.
- Ran the skill's `session-catchup.py`; unsynced context only contained repeated interrupted requests to use the skill, with no new technical result beyond the existing planning files.
- Re-read `task_plan.md`, `findings.md`, and `progress.md`; confirmed the project is already captured and Git diff is clean before this update.
- Confirmed `.codex/` is local Codex tooling/configuration and should stay untracked for now.
- User explicitly requested that this project use `planning-with-files` for all future work; recorded this as a project operating convention in `task_plan.md`.
- User clarified the broader project scope: deploy FastLIVO2 on a self-built handheld device, collect camera/LiDAR/synchronized data, transfer it into the local/server workflow, then run COLMAP or an equivalent pose/point-cloud stage, train 2DGS, and render/evaluate the reconstructed scene.
- Recorded FastLIVO2-to-2DGS without COLMAP as a candidate research direction that may be useful if FastLIVO2 can provide 2DGS-compatible poses, intrinsics, and point cloud data.
- User clarified that the severe star-like streak screenshots came from free-view movement in `2DGSmonitor`, not `render.py`.
- User provided four GT/render pairs for `reception_hall_balanced_v1`: blue sign, wall/sofa, plants, and fire cabinet.
- Observation: training-camera alignment is broadly correct, but the render is over-smoothed. Blue sign text is partly readable, plants preserve rough color/shape, but wall/sofa material detail and fire cabinet text/hard edges are heavily lost.
- Next experiment should prioritize detail recovery with `-r 1`, weaker `lambda_dist`, lower `opacity_cull`, and lower `densify_grad_threshold`.
- User clarified that monitor/free-view inspection shows wall protrusions from other viewpoints; the issue is not only over-smoothing in train-view renders.
- Revised diagnosis: the current dataset/model may be novel-view geometry limited. A reshoot is a serious option if final scene quality is the goal.

### 2026-07-08

- User captured a new 58-second fisheye-camera video at 10 Hz, producing about 580 extracted frames, and uploaded the frames to the AutoDL dataset folder.
- User has fisheye camera intrinsics and asked whether/how they can be used with COLMAP.
- Updated `convert.py` to support known COLMAP intrinsics through `--camera_params`.
- Updated `convert.py` to support `--matcher sequential`, which is better suited for video/frame sequences than exhaustive matching.
- Added fisheye-video conversion notes to `docs/2DGS_CHINESE_WORKFLOW.md`.
- User converted `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2` successfully with `OPENCV_FISHEYE`, known intrinsics, and sequential matching.
- COLMAP `model_analyzer` for `reception_hall_by_geoscanS2`:
  - Cameras: 1
  - Images: 598
  - Registered images: 598
  - Points: 21822
  - Observations: 506302
  - Mean track length: 23.201448
  - Mean observations per image: 846.658863
  - Mean reprojection error: 1.064254 px
- Interpretation: the fisheye-video COLMAP result is strong overall, with full registration and much better track length/observations than the old 129-image dataset, though reprojection error is slightly higher.
- User chose to run a full 30k-step training job for the fisheye dataset, instead of a 7k smoke test, to compare more directly with the previous 30k-step experiments.
- User compared fisheye input frames against COLMAP undistorted output images and found the output field of view is extremely small. Revised next step: inspect/tune fisheye undistortion before committing to the 30k 2DGS training run.
- User clarified that a 30k 2DGS run on the narrow-FOV fisheye COLMAP output was already completed:
  - Dataset: `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2`
  - Output: `/root/autodl-tmp/outputs/reception_hall_geoscanS2_30k_v1`
  - Iteration 30000 train L1: 0.009084
  - Iteration 30000 train PSNR: 37.131
  - Points: 230465
  - Render with `--skip_mesh` completed.
- User's main issue with this completed run is not whether it trains, but that the narrow undistorted field of view makes the reconstructed scene too small.
- User also ran `colmap image_undistorter` with `--blank_pixels 0.3 --max_image_size 1600` into `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_undistorter`; this wider-FOV undistorted dataset should be inspected before retraining.
- User checked image sizes:
  - input: `(1280, 1024)`
  - original COLMAP undistorted `images`: `(256, 204)`
  - `_undistorter` output with `--blank_pixels 0.3 --max_image_size 1600`: `(256, 204)`
- Interpretation: the `_undistorter` attempt did not change the effective undistorted image size/FOV. Do not train on `_undistorter` yet; first inspect `colmap image_undistorter -h` and try scale-related options such as `--min_scale`/`--max_scale` if available.
- User created `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_undistort_scale1` with explicit scale settings. Size check:
  - input: `(1280, 1024)`
  - original COLMAP undistorted `images`: `(256, 204)`
  - `undistort_scale1/images`: `(1280, 1024)`
- User visually checked images and said the result appears successful. This dataset is now the next candidate for a full 30k 2DGS comparison run.
- First training attempt on `reception_hall_by_geoscanS2_undistort_scale1` failed because 2DGS could not find `sparse/0/images.bin` or `sparse/0/images.txt`. Likely cause: COLMAP `image_undistorter` wrote the reconstruction files under `sparse/` directly instead of `sparse/0/`, or did not write the expected model files into the new output path. Next diagnostic is to list the dataset tree and copy/move `cameras.*`, `images.*`, and `points3D.*` into `sparse/0/` if they exist.

### 2026-07-09

- User resolved the dataset structure issue and completed the full-size fisheye training run.
- Free-view comparison shows a tradeoff: the narrow-FOV run keeps the sign text sharper but has poorer sofa/blue-structure continuity; the full-size run improves scene continuity but softens text.
- Both runs show wall/blue-LED-region protrusions from oblique free views.
- Updated diagnosis: the dominant limitation is now capture geometry plus difficult low-texture/emissive/reflective surfaces, not simply image count or undistorted field of view.
- Next action is a deliberate reshoot with translated low/mid/high passes, left/right oblique views, and close detail passes.
- Confirmed training semantics from source: one iteration uses one camera; cameras are sampled randomly without replacement until every training camera has been used, then the list is refilled.
- Consequently, 3000 training images over 30000 iterations receive about 10 updates each. Recommended selecting roughly 600-1200 high-value keyframes for the next hall baseline rather than retaining every 10 Hz video frame.
- User completed a second fisheye capture using translated multi-height and oblique passes. New input path: `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_v2/input`.
- Decided to run COLMAP SfM once, preserve its default narrow undistortion output, and generate a separate full-size `scale1` output as the primary v2 training dataset.
- COLMAP completed successfully for `reception_hall_by_geoscanS2_v2`: 298/298 images registered, 18541 points, mean track length 7.08, and mean reprojection error 0.8065 px.
- The v2 sparse reconstruction is accepted for the next full-size `scale1` undistortion step.

## Latest Known Server Commands

Check repository state on AutoDL:

```bash
cd /root/autodl-tmp/noob_2dgs
git pull --ff-only
git status --short
git rev-parse HEAD
```

Recommended next training run:

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

Recommended detail-preserving run if wall text remains poor:

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

Render check without mesh:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --skip_mesh
```

Mesh check:

```bash
python render.py \
  -s /root/autodl-tmp/datasets/reception_hall_colmap \
  -m /root/autodl-tmp/outputs/reception_hall_balanced_v1 \
  --unbounded \
  --skip_train \
  --skip_test \
  --mesh_res 1024 \
  --num_cluster 20
```

## Open Questions

- Does `reception_hall_balanced_v1` preserve wall text better than `reception_hall_clean_v1`?
- Is `-r 1` feasible on the current RTX 3090 memory budget?
- Should the server use a custom COLMAP 3.9.1 CUDA build permanently?
- Should `ffmpeg`, `dash==2.14.2`, and `comm==0.1.4` be added to a server setup note or install script?
- Should future experiments save screenshots/renders into a structured comparison directory?
- What exact data products will the handheld device export: images only, image timestamps, LiDAR scans, IMU, calibrated camera-LiDAR extrinsics, FastLIVO2 trajectory, colored point cloud?
- Can FastLIVO2 outputs be converted into COLMAP-compatible `sparse/0` files for direct 2DGS training?
- What exact fisheye calibration model does the camera intrinsics use: OpenCV fisheye `fx,fy,cx,cy,k1,k2,k3,k4`, ordinary OpenCV radial/tangential, or another model?
- New fisheye frame dataset path on AutoDL is `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2`.

## Next Assistant Actions

1. Keep using `task_plan.md`, `findings.md`, and `progress.md` as the persistent working memory for this project.
2. Have the user run a full 30k-step comparison training on `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_undistort_scale1`.
3. Render the `undistort_scale1` run with `--skip_mesh`, then compare scene extent, wall stability, and detail retention against the narrow-FOV fisheye baseline.
4. Render train views and inspect monitor/free-view geometry against the old `reception_hall_colmap` results.
5. If the new fisheye dataset improves wall stability, promote it as the new baseline dataset.
6. If quality is still poor, inspect video frame blur/overlap and fisheye undistortion artifacts.
7. After every new server experiment or code change, update `progress.md`; if the result changes what we believe, also update `findings.md` and `task_plan.md`.
