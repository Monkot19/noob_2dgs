# 2DGS 输出管理规范

这个项目的输出会越来越多，核心原则是：不要靠目录名硬记结论。每个实验至少要能回答四件事：

1. 用的是哪个数据集。
2. 训练命令和关键参数是什么。
3. 最终指标和点云规模是什么。
4. 视觉结论是什么，下一步是否还值得沿着这个方向做。

## 当前输出根目录

本地整理目录：

```text
D:\workspace\2DGS_output
```

AutoDL 常用输出目录：

```text
/root/autodl-tmp/outputs
```

建议服务器训练完成后，把需要长期比较的 run 同步到本地 `D:\workspace\2DGS_output`，然后刷新索引。

## 命名规则

推荐格式：

```text
<scene>_<capture-or-dataset>_<fov-or-preprocess>_<purpose>_<iterations>_<version>
```

字段含义：

- `scene`: 场景名，例如 `reception_hall`。
- `capture-or-dataset`: 数据来源，例如 `colmap`、`geoscanS2`、`geoscanS2_v2`。
- `fov-or-preprocess`: 关键预处理，例如 `narrow`、`scale1`、`undistort`。
- `purpose`: 实验目的，例如 `baseline`、`clean`、`detail`、`text`。
- `iterations`: 训练轮数，例如 `30k`、`60k`。
- `version`: 同类实验版本，例如 `v1`、`v2`。

例子：

```text
reception_hall_geoscanS2_v2_scale1_baseline_30k_v1
reception_hall_geoscanS2_v2_narrow_text_30k_v1
reception_hall_geoscanS2_v2_scale1_detail_60k_v1
```

已经存在的旧目录可以先不强行重命名，避免和服务器路径、截图说明对不上。新实验从这套规则开始即可。

## 自动生成索引

仓库里提供了脚本：

```powershell
python D:\workspace\2DGS\scripts\output_inventory.py D:\workspace\2DGS_output
```

它会生成：

```text
D:\workspace\2DGS_output\RUN_INDEX.md
D:\workspace\2DGS_output\RUN_INDEX.csv
```

索引会扫描每个 run 的：

- `cfg_args`
- `train.log`
- `render.log`
- `point_cloud/iteration_*/point_cloud.ply`
- `train/`
- `traj/`

它不会移动、删除或覆盖训练结果，只会刷新索引文件。

## 每个实验建议保留

必须保留：

- `cfg_args`
- `train.log`
- 最终 `point_cloud/iteration_30000/point_cloud.ply` 或对应最终迭代点云
- 关键渲染结果或截图
- 实验结论

建议保留：

- `render.log`
- `cameras.json`
- `input.ply`
- 用于对比的 GT/render crop

可以后续归档或删除：

- TensorBoard `events.out.tfevents.*`
- 中间迭代点云，例如 `iteration_7000`
- 全量 `train/ours_30000/renders`，前提是已经保存关键对比图

## 视觉结论记录格式

建议在 `D:\workspace\2DGS_output\RUN_NOTES.md` 里人工维护视觉结论。自动索引文件可以反复生成，不要把人工结论直接写进 `RUN_INDEX.md`。

模板：

```markdown
## reception_hall_geoscanS2_v2_scale1_30k_v1

- Dataset: `/root/autodl-tmp/datasets/reception_hall_by_geoscanS2_v2_undistort_scale1`
- Command: `python train.py ...`
- Good:
  - 墙面不再分层。
  - 蓝色灯带右侧不再凸出。
- Bad:
  - 招牌文字仍偏软。
- Verdict: 作为当前结构 baseline 保留。
- Next: 和 narrow 版本做同视角 crop 对比。
```

## 比较实验时的固定流程

1. 先刷新索引，确认两个 run 的数据集、迭代数、点云数量。
2. 只比较同一类输出：训练视角 render 对 render，自由视角 monitor 对 monitor。
3. 对文字、消防柜、植物叶片等细节，用同一视角、同一缩放比例裁剪对比。
4. 每次比较后，把结论写进 `RUN_NOTES.md` 和项目根目录的 `progress.md`。

