# 2DGS 从图片数据集到训练、渲染的完整流程

本文档记录本仓库在 Ubuntu / AutoDL 服务器上的推荐使用流程。目标是从“一组普通图片”开始，经过 COLMAP 重建相机位姿，再训练 2D Gaussian Splatting，最后渲染图片或导出网格。

## 1. 整体流程

完整流程如下：

```text
原始图片
  -> 整理为 input/ 目录
  -> COLMAP 估计相机位姿和稀疏点云
  -> 生成 2DGS 可读的数据集结构 images/ + sparse/0/
  -> train.py 训练 2DGS 模型
  -> render.py 渲染图片、深度、法线或导出网格
```

如果你已经有 COLMAP 格式数据集，可以跳过 COLMAP 转换步骤，直接训练。

## 2. 推荐目录结构

在 AutoDL 上建议把代码、数据和输出都放在 `/root/autodl-tmp`，避免占用系统盘。

```text
/root/autodl-tmp/
├── noob_2dgs/                 # 本代码仓库
├── datasets/
│   └── my_scene/
│       └── input/             # 原始图片放这里
└── outputs/
    └── my_scene/              # 训练输出放这里
```

其中 `my_scene` 可以换成你的场景名。

## 3. 克隆代码

```bash
cd /root/autodl-tmp
git clone --recursive https://github.com/Monkot19/noob_2dgs.git
cd noob_2dgs
```

如果克隆时没有带 `--recursive`，需要补拉子模块：

```bash
git submodule update --init --recursive
```

## 4. 检查服务器环境

先确认 GPU、CUDA 编译器和 PyTorch 都正常：

```bash
nvidia-smi
nvcc --version
python --version
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

理想情况类似：

```text
GPU: RTX 3090 / RTX 4090 / A 系列显卡
nvcc: 11.8
Python: 3.8.x
PyTorch: 2.0.0+cu118
torch.cuda.is_available(): True
```

如果 AutoDL 镜像已经自带合适的 PyTorch 和 CUDA，不建议强行执行：

```bash
conda env create --file environment.yml
```

这个文件比较旧，Conda 解依赖可能会卡很久。更稳的做法是在当前基础环境里补装项目依赖。

## 5. 安装 Python 依赖和 CUDA 扩展

进入仓库目录：

```bash
cd /root/autodl-tmp/noob_2dgs
```

安装普通 Python 依赖：

```bash
pip install open3d==0.18.0 mediapy==1.1.2 lpips==0.1.4 scikit-image==0.21.0 tqdm==4.66.2 trimesh==4.3.2 plyfile opencv-python
```

编译并安装 2DGS 需要的 CUDA 扩展：

```bash
pip install submodules/diff-surfel-rasterization
pip install submodules/simple-knn
```

验证扩展是否安装成功：

```bash
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"
```

看到下面输出就说明环境基本可用：

```text
extensions ok
```

## 6. 准备只有图片的数据集

假设场景名为 `my_scene`，先创建目录：

```bash
mkdir -p /root/autodl-tmp/datasets/my_scene/input
```

把所有原始图片放到：

```text
/root/autodl-tmp/datasets/my_scene/input/
```

推荐图片命名简单一些，例如：

```text
0001.jpg
0002.jpg
0003.jpg
...
```

图片拍摄建议：

- 图片之间要有足够重叠，不要每张都差太远。
- 尽量围绕同一个物体或场景多角度拍摄。
- 避免大量模糊、反光、纯色墙面、透明物体。
- 光照尽量稳定，不要一部分过曝、一部分太暗。
- 小物体可以绕物体拍，大场景可以沿路径移动拍。

## 7. 安装或检查 COLMAP

`convert.py` 会调用系统里的 `colmap` 命令，所以先检查：

```bash
colmap -h
```

如果提示 `command not found`，在 Ubuntu 上安装：

```bash
apt update
apt install -y colmap
```

安装后再次检查：

```bash
colmap -h
```

## 8. 用 COLMAP 转换图片数据集

进入代码仓库：

```bash
cd /root/autodl-tmp/noob_2dgs
```

运行转换：

```bash
python convert.py -s /root/autodl-tmp/datasets/my_scene
```

`convert.py` 默认会读取：

```text
/root/autodl-tmp/datasets/my_scene/input/
```

并生成：

```text
/root/autodl-tmp/datasets/my_scene/
├── input/
├── distorted/
├── images/
└── sparse/
    └── 0/
```

其中 `images/` 和 `sparse/0/` 是训练 2DGS 需要的关键目录。

如果服务器没有可用的 COLMAP GPU 支持，可以尝试 CPU 模式：

```bash
python convert.py -s /root/autodl-tmp/datasets/my_scene --no_gpu
```

CPU 模式会慢一些。

如果图片尺寸不完全一致，例如有的图片是横屏、有的是竖屏，或者部分图片被裁剪过，默认单相机模式会报：

```text
Single camera specified, but images have different dimensions.
```

这时可以让 COLMAP 为每张图片单独估计相机内参：

```bash
python convert.py -s /root/autodl-tmp/datasets/my_scene --no_gpu --camera_per_image
```

更理想的做法是先把所有图片整理成相同分辨率和方向，再使用默认单相机模式。默认模式通常更适合来自同一台相机、同一焦距的一组图片。

## 9. 检查 COLMAP 转换是否成功

转换完成后检查：

```bash
ls /root/autodl-tmp/datasets/my_scene/images
ls /root/autodl-tmp/datasets/my_scene/sparse/0
```

`sparse/0` 下通常应该有：

```text
cameras.bin
images.bin
points3D.bin
```

如果没有这些文件，说明 COLMAP 没有成功重建。常见原因是：

- 图片重叠太少。
- 场景纹理太少，特征点不够。
- 图片太模糊。
- 拍摄路径跨度太大。
- 多个物体或背景变化太大。

## 10. 开始训练

创建输出目录：

```bash
mkdir -p /root/autodl-tmp/outputs
```

训练：

```bash
cd /root/autodl-tmp/noob_2dgs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

如果图片分辨率很高，显存压力大，可以降低训练分辨率：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2
```

如果是无界大场景，通常建议使用平均深度：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --depth_ratio 0
```

如果是类似 DTU 这种前景物体、边界相对明确的场景，可以尝试：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2 --depth_ratio 1
```

## 11. 用 tmux 跑长任务

训练通常需要较长时间，建议用 `tmux`，这样断开网页或 SSH 后训练不会停。

新建会话：

```bash
tmux new -s 2dgs
```

在 tmux 里运行训练：

```bash
cd /root/autodl-tmp/noob_2dgs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

临时离开 tmux：

```text
Ctrl+b 然后按 d
```

重新进入：

```bash
tmux attach -t 2dgs
```

## 12. 渲染测试集图片

训练完成后，可以渲染结果：

```bash
cd /root/autodl-tmp/noob_2dgs
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```

## 22. 鱼眼相机视频抽帧数据

如果数据来自鱼眼相机视频抽帧，建议优先把鱼眼内参提供给 COLMAP，而不是让 COLMAP 从零估计普通 OPENCV 相机。

### 22.1 推荐数据结构

```text
/root/autodl-tmp/datasets/fisheye_scene/
└── input/
    ├── 000001.jpg
    ├── 000002.jpg
    └── ...
```

同一段视频抽帧通常来自同一台相机、同一分辨率、同一内参，所以不要使用 `--camera_per_image`，保持单相机模式更合理。

### 22.2 使用鱼眼内参跑 COLMAP

如果标定结果是 OpenCV fisheye 模型，参数顺序通常是：

```text
fx,fy,cx,cy,k1,k2,k3,k4
```

示例：

```bash
cd /root/autodl-tmp/noob_2dgs

python convert.py \
  -s /root/autodl-tmp/datasets/fisheye_scene \
  --camera OPENCV_FISHEYE \
  --camera_params "fx,fy,cx,cy,k1,k2,k3,k4" \
  --matcher sequential
```

把上面的 `fx,fy,cx,cy,k1,k2,k3,k4` 换成真实标定值。

`--matcher sequential` 适合视频抽帧，因为相邻帧天然连续；默认 exhaustive matcher 会做大量两两匹配，580 张图会比较慢。

### 22.3 重要限制

2DGS 训练阶段不直接读取鱼眼相机模型。正确流程是：

```text
鱼眼 input/
  -> COLMAP 使用 OPENCV_FISHEYE 建图
  -> COLMAP image_undistorter 输出去畸变 images/ 和 PINHOLE sparse/0
  -> 2DGS 读取 images/ + sparse/0
```

也就是说，鱼眼模型只用于 COLMAP 的前半段；`convert.py` 后面的 `image_undistorter` 会把它转成 2DGS 可读的针孔模型。

### 22.4 如果 COLMAP 仍然困难

- 先确认所有抽帧分辨率一致。
- 视频 10Hz 抽出的 580 张图可能相邻帧过密；如果匹配慢或质量差，可以尝试每 2-3 帧取一张。
- 避免运动模糊严重的帧。
- 如果是室内弱纹理墙面，拍摄时需要斜视角、环绕、回环和足够视差。
- 跑完后用 `colmap model_analyzer --path <dataset>/sparse/0` 检查注册帧数、点数、track length 和 reprojection error。

## 17. train.py 参数详解

本节只解释日常最常用、最影响结果的参数。默认参数定义在 `arguments/__init__.py`，训练主逻辑在 `train.py`。

### 17.1 数据与输出

`-s` / `--source_path`

数据集路径。必须指向已经完成 COLMAP 转换的数据集目录，目录里至少应有：

```text
images/
sparse/0/
```

例子：

```bash
-s /root/autodl-tmp/datasets/reception_hall_colmap
```

`-m` / `--model_path`

模型输出路径。建议每次实验用不同目录，不要覆盖旧结果：

```bash
-m /root/autodl-tmp/outputs/reception_hall_balanced_v1
```

输出目录中常见内容：

```text
cfg_args                  # 本次训练参数记录
point_cloud/              # 保存的高斯点云
events.out...             # TensorBoard 日志
chkpnt*.pth               # checkpoint，只有指定 checkpoint_iterations 才有
```

`--images`

指定读取的图片目录名，默认是 `images`。一般不要改。只有当你手动准备了 `images_2`、`images_4` 等目录并希望直接训练它们时才需要改。

### 17.2 分辨率与显存

`-r` / `--resolution`

控制训练读入图片的分辨率。

默认 `-1`：如果图片宽度超过约 1600 像素，会自动缩到约 1600。适合大多数场景。

`-r 1`：使用原始分辨率。细节更好，例如墙上文字、小标识、纹理，但显存和时间开销更大。

`-r 2`：使用 1/2 分辨率。更省显存、更快，适合快速试验或显存不足。

`-r 4`：使用 1/4 分辨率。只建议用于快速检查流程，不适合最终效果。

推荐：

```bash
# 快速试跑
-r 2

# 正式训练，保留小字和细节
-r 1

# 默认稳妥
不写 -r
```

### 17.3 训练步数与保存

`--iterations`

训练总步数，默认 `30000`。

推荐：

```bash
# 快速看趋势
--iterations 7000

# 常规正式训练
--iterations 30000

# 复杂室内、大场景、细节多
--iterations 40000
```

步数更多不一定更好。如果正则不合适，训练更久可能只是把错误几何训练得更明显。

`--save_iterations`

保存高斯结果的迭代点，默认保存 `7000` 和 `30000`，代码还会自动追加最终 `iterations`。

```bash
--save_iterations 10000 20000 30000
```

`--test_iterations`

在哪些迭代点做测试集评估，默认 `7000 30000`。如果只关心最终结果，可以：

```bash
--test_iterations 30000
```

`--checkpoint_iterations`

保存可恢复训练的 checkpoint。注意 checkpoint 和普通保存的高斯点云不同，checkpoint 用于断点续训。

```bash
--checkpoint_iterations 10000 20000 30000
```

`--start_checkpoint`

从 checkpoint 恢复训练：

```bash
--start_checkpoint /root/autodl-tmp/outputs/my_scene/chkpnt20000.pth
```

### 17.4 几何正则相关参数

`--depth_ratio`

控制渲染深度的统计方式，默认 `0.0`。

`--depth_ratio 0`：使用 mean depth。适合大多数室内、室外、大场景、深度跨度大的场景。大厅、走廊、房间、街景通常先用这个。

`--depth_ratio 1`：使用 median depth。适合前景物体明确、边界干净、类似 DTU 扫描物体的数据。

经验：

```bash
# 室内大厅、走廊、办公室、室外
--depth_ratio 0

# 单个物体、桌面物体、边界明确的扫描
--depth_ratio 1
```

`--lambda_normal`

法线一致性正则，默认 `0.05`，训练到 7000 步之后才生效。它会让表面更平滑、更像连续面。

调大后：

- 墙面、地面更平。
- mesh 通常更干净。
- 但墙上的字、小纹理、细薄结构可能被抹平，甚至被解释成异常几何突起。

推荐范围：

```bash
# 保细节
--lambda_normal 0.01
--lambda_normal 0.03

# 默认稳妥
--lambda_normal 0.05

# 更重视几何平整
--lambda_normal 0.1
```

`--lambda_dist`

深度 distortion 正则，默认 `0.0`，训练到 3000 步之后才生效。它常用于压制空间中的漂浮高斯和沿视线方向散开的高斯。

调大后：

- floaters 通常会减少。
- 空间更干净。
- 但纹理细节可能变糊，小字可能不清楚。
- 过大时几何可能收缩或墙面出现不自然突起。

推荐范围：

```bash
# 保纹理，轻度约束
--lambda_dist 10

# 平衡 floaters 与细节
--lambda_dist 50

# 明显压制漂浮高斯
--lambda_dist 100

# 强压制，只在 floaters 很严重时试
--lambda_dist 1000
```

### 17.5 高斯增殖与剪枝

`--densify_from_iter`

从第几步开始增殖高斯，默认 `500`。一般不改。

`--densify_until_iter`

到第几步停止增殖高斯，默认 `15000`。

调小后：

- 高斯数量更少。
- 空间更干净。
- 但细节可能不足。

推荐：

```bash
# 默认
--densify_until_iter 15000

# floaters 多，想让模型少长一些高斯
--densify_until_iter 12000

# 细节很多，想给模型更多增长空间
--densify_until_iter 18000
```

`--densification_interval`

每隔多少步做一次增殖/剪枝，默认 `100`。一般不改。

`--densify_grad_threshold`

控制哪些区域会长出新高斯，默认 `0.0002`。

调大后：

- 更难长出新高斯。
- floaters 可能减少。
- 细节可能变少，小字、细线、边缘更容易糊。

调小后：

- 更容易长出高斯。
- 细节可能更多。
- 但空间可能更乱。

推荐：

```bash
# 保细节
--densify_grad_threshold 0.00025
--densify_grad_threshold 0.0003

# 默认
--densify_grad_threshold 0.0002

# 压制杂乱高斯
--densify_grad_threshold 0.0004
--densify_grad_threshold 0.0005
```

`--opacity_cull`

剪掉低 opacity 高斯的阈值，默认 `0.05`。

调大后：

- 更积极删除弱贡献高斯。
- 空间更干净。
- 但细节和半透明/细薄结构可能损失。

推荐：

```bash
# 保守剪枝
--opacity_cull 0.05

# 稍微清理 floaters
--opacity_cull 0.08

# 更强清理
--opacity_cull 0.1
--opacity_cull 0.15
```

`--opacity_reset_interval`

每隔多少步重置 opacity，默认 `3000`。一般不改。

### 17.6 外观与优化参数

`--lambda_dssim`

L1 和 SSIM 图像损失之间的权重，默认 `0.2`。一般不改。

调大后更重视结构相似性，调小后更重视逐像素颜色。多数场景默认即可。

`--sh_degree`

球谐颜色阶数，默认 `3`。控制视角相关颜色表达能力。一般不改。

`--white_background`

白色背景。适合物体数据集或白底合成数据。真实室内/室外 COLMAP 数据通常不要加。

`--eval`

开启训练/测试集划分。想看 PSNR 等测试指标时可以加。图片数量不多、希望所有图都参与训练时不要加。

`--data_device`

默认 `cuda`。一般不改。

`--position_lr_init`、`--position_lr_final`、`--feature_lr`、`--opacity_lr`、`--scaling_lr`、`--rotation_lr`

这些是不同参数组的学习率。除非你明确知道要改什么，否则不建议动。调几何问题时，优先调 `lambda_dist`、`lambda_normal`、`opacity_cull`、`densify_grad_threshold`。

## 18. train.py 典型场景配置

### 18.1 快速验证流程

适合刚转换完数据，想确认能不能训练。

```bash
python train.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene_test \
  -r 2 \
  --iterations 7000
```

### 18.2 室内大厅、走廊、办公室

适合 `reception_hall` 这类场景。先用平衡配置：

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

如果空间中漂浮高斯仍然多：

```bash
--lambda_dist 100
--opacity_cull 0.1
--densify_grad_threshold 0.0004
```

如果墙上文字、标识、纹理变糊或变成突起：

```bash
--lambda_normal 0.03
--lambda_dist 10
--densify_grad_threshold 0.00025
-r 1
```

### 18.3 墙面文字、小标识、纹理细节很重要

优先保细节：

```bash
python train.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene_detail_v1 \
  -r 1 \
  --depth_ratio 0 \
  --lambda_normal 0.03 \
  --lambda_dist 10 \
  --opacity_cull 0.08 \
  --densify_grad_threshold 0.00025
```

如果显存不够，把 `-r 1` 去掉，让它自动缩到约 1600 宽。

### 18.4 漂浮高斯很多，空间很乱

偏向清理 floaters：

```bash
python train.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene_clean_v1 \
  --depth_ratio 0 \
  --lambda_normal 0.1 \
  --lambda_dist 100 \
  --opacity_cull 0.1 \
  --densify_grad_threshold 0.0004 \
  --densify_until_iter 12000
```

如果清理后细节损失明显，优先把 `lambda_normal` 降到 `0.05`，再把 `lambda_dist` 降到 `50`。

### 18.5 单个物体、桌面物体、边界明确

类似 DTU 或小物体环绕拍摄：

```bash
python train.py \
  -s /root/autodl-tmp/datasets/object_scene \
  -m /root/autodl-tmp/outputs/object_scene_v1 \
  -r 2 \
  --depth_ratio 1 \
  --lambda_normal 0.05 \
  --lambda_dist 10
```

如果背景干净、希望 mesh 更平滑，可以试：

```bash
--lambda_normal 0.1
--lambda_dist 50
```

### 18.6 室外或无界大场景

室外、大空间、深度跨度大：

```bash
python train.py \
  -s /root/autodl-tmp/datasets/outdoor_scene \
  -m /root/autodl-tmp/outputs/outdoor_scene_v1 \
  --depth_ratio 0 \
  --lambda_normal 0.05 \
  --lambda_dist 10
```

如果远处漂浮物明显，再增加：

```bash
--lambda_dist 50
```

### 18.7 显存不足

优先按这个顺序降压力：

```bash
# 1. 降分辨率
-r 2

# 2. 减少训练步数做试验
--iterations 7000

# 3. 停止更早增殖
--densify_until_iter 12000

# 4. 提高增殖门槛
--densify_grad_threshold 0.0004
```

## 19. render.py 参数详解

`render.py` 既可以导出训练/测试视角渲染图，也可以生成轨迹视频，还可以融合网格。

基础命令：

```bash
python render.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene
```

### 19.1 输入输出参数

`-s` / `--source_path`

数据集路径。建议渲染时也明确写上，避免只靠 `cfg_args`。

`-m` / `--model_path`

训练输出路径。

`--iteration`

指定加载哪一次保存的模型。默认 `-1`，加载最新一次。

```bash
--iteration 30000
```

### 19.2 控制导出内容

`--skip_train`

不导出训练视角渲染。

`--skip_test`

不导出测试视角渲染。

`--skip_mesh`

不导出 mesh。只想看渲染图或视频时建议加上，可以省很多时间。

`--render_path`

生成一条相机轨迹并导出视频。需要系统安装 `ffmpeg`：

```bash
apt update
apt install -y ffmpeg
```

如果只想先验证模型质量：

```bash
python render.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene \
  --skip_mesh
```

如果只想导出视频：

```bash
python render.py \
  -s /root/autodl-tmp/datasets/my_scene \
  -m /root/autodl-tmp/outputs/my_scene \
  --render_path \
  --skip_train \
  --skip_test \
  --skip_mesh
```

### 19.3 有界 mesh 参数

默认不加 `--unbounded` 时使用有界 TSDF 融合。

`--mesh_res`

有界模式下，如果没有手动指定 `voxel_size`，代码会用：

```text
voxel_size = depth_trunc / mesh_res
```

因此 `mesh_res` 越大，网格越细，越耗显存和时间。

`--depth_trunc`

TSDF 融合时保留的最大深度范围。日志里会提示类似：

```text
Use at least 4.92 for depth_trunc
```

如果 mesh 断裂、远处缺失，可以调大：

```bash
--depth_trunc 5.0
```

如果远处噪声很多，可以调小。

`--voxel_size`

体素大小。越小 mesh 越细，但更慢更吃显存。室内场景可试：

```bash
--voxel_size 0.01
--voxel_size 0.005
```

`--sdf_trunc`

TSDF 截断距离。默认是 `5 * voxel_size`。一般不改。

`--num_cluster`

mesh 后处理保留的连通块数量，默认 `50`。

调小可以删除更多孤立碎片：

```bash
--num_cluster 10
--num_cluster 20
```

如果场景本来有很多分离物体，调太小会误删。

### 19.4 无界 mesh 参数

`--unbounded`

使用无界 mesh 提取，适合室外、大空间、边界不明确场景，也适合大厅这种范围较大的室内空间。

`--mesh_res`

无界模式下控制网格分辨率：

```bash
--mesh_res 512     # 快速、粗糙、省显存
--mesh_res 1024    # 常用
--mesh_res 2048    # 更细，开销大
```

室内大厅建议先试：

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

### 19.5 render.py 典型命令

只导出训练视角和测试视角图片，不导 mesh：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_mesh
```

只导视频：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --render_path --skip_train --skip_test --skip_mesh
```

导出无界 mesh：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --unbounded --skip_train --skip_test --mesh_res 1024 --num_cluster 20
```

导出有界 mesh：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train --skip_test --mesh_res 1024 --depth_trunc 5.0 --num_cluster 20
```

## 20. 常见现象与调参方向

### 20.1 空间里有很多彩色漂浮高斯

优先尝试：

```bash
--lambda_dist 50 或 100
--opacity_cull 0.08 或 0.1
--densify_grad_threshold 0.0003 或 0.0004
```

如果仍然多，再试：

```bash
--densify_until_iter 12000
--lambda_normal 0.1
```

### 20.2 墙面更平了，但墙上文字看不清

说明几何正则或剪枝太强。优先尝试：

```bash
--lambda_normal 0.03
--lambda_dist 10
--densify_grad_threshold 0.00025
-r 1
```

### 20.3 墙上文字变成异常突起

常见于模型把高频纹理当成几何。尝试降低几何正则：

```bash
--lambda_normal 0.03
--lambda_dist 10 或 50
```

同时用 `-r 1` 保留原图细节，让模型更容易用颜色解释文字，而不是用几何解释文字。

### 20.4 mesh 碎片很多

渲染 mesh 时调：

```bash
--num_cluster 10
--num_cluster 20
```

训练时调：

```bash
--opacity_cull 0.1
--lambda_dist 50
```

### 20.5 渲染图清楚，但点云看起来乱

这是正常现象的一部分。2DGS/3DGS 的高斯点云不是传统 SfM 点云，里面会有一些服务于渲染的高斯。判断结果时优先看：

- novel view 渲染图
- depth / normal
- mesh 后处理结果

不要只用裸 ply 点云的干净程度判断模型是否失败。

## 21. 上下文用完后如何迁移到新对话

如果这个对话的上下文快用完，或者你想开一个新项目继续，建议按下面方式迁移。

### 21.1 最重要的原则

代码和文档已经在 GitHub 仓库里，这是最可靠的“长期记忆”：

```text
https://github.com/Monkot19/noob_2dgs.git
```

新对话里只要告诉我仓库地址、服务器路径、当前问题，我就能继续。

### 21.2 新对话开头建议直接贴这段

```text
我们之前在做 2D Gaussian Splatting 项目，仓库是：
https://github.com/Monkot19/noob_2dgs.git

本地路径：
D:\workspace\2DGS

AutoDL 服务器路径：
/root/autodl-tmp/noob_2dgs

数据集：
/root/autodl-tmp/datasets/reception_hall_colmap

主要输出：
/root/autodl-tmp/outputs/

当前环境：
AutoDL Ubuntu，PyTorch 2.0.0+cu118，CUDA 11.8，RTX 3090。
diff_surfel_rasterization 和 simple_knn 已安装成功。

COLMAP：
系统自带 /usr/bin/colmap 是 3.6 without CUDA；
后来参考旧记录编译/使用过 COLMAP 3.9.1 with CUDA 的方案。

当前已完成：
1. GitHub fork/自有仓库已建立。
2. 子模块已初始化。
3. reception_hall 图片已通过 COLMAP 转换，129 张图注册成功，9715 points，mean reprojection error 约 0.96px。
4. 可以训练和渲染。
5. 当前主要问题是训练结果中有漂浮高斯、墙面文字和几何正则之间需要调参平衡。

请先读取 docs/2DGS_CHINESE_WORKFLOW.md，然后接着帮我处理当前问题。
```

### 21.3 每次服务器报错时建议提供

```bash
cd /root/autodl-tmp/noob_2dgs
git rev-parse HEAD
git status --short
```

同时贴：

- 你执行的完整命令
- 完整报错
- 当前使用的数据集路径
- 当前输出目录
- 你想改善的具体现象，例如 floaters、多余突起、文字不清、mesh 破碎

### 21.4 如何让新对话拿到最新代码

服务器上：

```bash
cd /root/autodl-tmp/noob_2dgs
git pull --ff-only
git submodule update --init --recursive
```

本地新环境中：

```bash
git clone --recursive https://github.com/Monkot19/noob_2dgs.git
```

如果只想渲染，不重新处理训练集或测试集，可以根据需要加：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train
```

或者：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_test
```

渲染结果通常会保存在模型输出目录下的相关子目录中。

## 13. 导出网格

### 13.1 有界场景网格

适合物体或边界明确的场景：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train --skip_test
```

可以根据效果调：

```bash
--voxel_size
--depth_trunc
--depth_ratio
```

例如：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --skip_train --skip_test --voxel_size 0.004 --depth_trunc 3.0
```

### 13.2 无界场景网格

适合室外、大范围或边界不明确的场景：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --unbounded --skip_train --skip_test --mesh_res 1024
```

`mesh_res` 越大，网格越细，但显存和时间开销也越大。显存不够时可以尝试：

```bash
--mesh_res 512
```

## 14. 常见问题

### 14.1 COLMAP 失败

表现：

```text
Feature extraction failed
Feature matching failed
Mapper failed
```

排查：

```bash
ls /root/autodl-tmp/datasets/my_scene/input
```

确认图片确实在 `input/` 下。

如果图片太少、重叠太低或特征太少，COLMAP 可能无法重建。需要重新拍摄或补充图片。

### 14.2 CUDA 扩展导入失败

重新安装两个子模块：

```bash
cd /root/autodl-tmp/noob_2dgs
pip install submodules/diff-surfel-rasterization --force-reinstall
pip install submodules/simple-knn --force-reinstall
```

再验证：

```bash
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"
```

### 14.3 显存不够

可以尝试：

```bash
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene -r 2
```

或者减少网格分辨率：

```bash
python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene --unbounded --mesh_res 512
```

### 14.4 训练效果差

常见原因：

- COLMAP 稀疏点云质量差。
- 图片数量太少。
- 视角覆盖不完整。
- 场景中反光、透明、纯色区域太多。
- 相机曝光和白平衡变化太大。

建议先检查 COLMAP 输出是否合理，再考虑调训练参数。

## 15. 后续代码更新

本地修改代码并推送到 GitHub 后，服务器更新：

```bash
cd /root/autodl-tmp/noob_2dgs
git pull --ff-only
git submodule update --init --recursive
```

如果更新涉及 CUDA 子模块或依赖，重新安装：

```bash
pip install submodules/diff-surfel-rasterization --force-reinstall
pip install submodules/simple-knn --force-reinstall
```

## 16. 推荐的最小命令顺序

如果你已经把图片放入 `input/`，可以按下面顺序执行：

```bash
cd /root/autodl-tmp/noob_2dgs

python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import diff_surfel_rasterization, simple_knn; print('extensions ok')"

python convert.py -s /root/autodl-tmp/datasets/my_scene

mkdir -p /root/autodl-tmp/outputs
python train.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene

python render.py -s /root/autodl-tmp/datasets/my_scene -m /root/autodl-tmp/outputs/my_scene
```
