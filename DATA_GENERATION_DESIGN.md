# 仿真数据生成设计

本项目把“一个仿真算例”定义为一份完整 JSON 配置。配置内容分开记录几何、初值、热风、材料、传热传质、收缩模型、数值设置和输出字段。任何物理参数变化都会生成新的稳定 `case_id`，便于断点续算、去重和追溯。

默认 DOE 使用可复现的 Latin hypercube，在以下范围覆盖主要不确定性：药材长度/半径、初始温度/含水率、热风温度/湿度/速度、导热系数、水分扩散系数和表面对流系数。扩散系数、传质系数跨数量级，使用对数采样。

数据集在运行仿真前固定分为 train/validation/test，避免后续按仿真结果人工拆分造成数据泄漏。默认 128 个设计点用于检查流程；生产数据规模应在模型完成并做网格与时间步收敛验证后决定。

每个求解输出建议采用以下约定：

- `case.json`：完整输入、单位、模型版本、case ID、随机种子和数据集划分。
- `fields.h5`：`time_s`、`r_m`、`z_m`、`temperature_K`、`moisture_kg_per_kg_dry`；移动网格时每个时刻保存坐标。
- `observables.csv`：平均温度、平均含水率、中心/表面值、半径、质量损失等低维量。
- `status.json`：PENDING/RUNNING/SUCCEEDED/FAILED、开始结束时间、运行耗时、收敛信息和错误摘要。

建议分阶段加入工况：

1. 固定几何、常物性、无收缩，先验证热湿耦合守恒。
2. 采样热风温度、相对湿度、速度和初始含水率，生成 baseline 数据。
3. 加入材料参数不确定性，用于代理模型稳健性。
4. 加入规定收缩，再升级 ALE；分别保留模型标签。
5. 若热风条件随时间变化，将工况改成分段 schedule，并为 schedule 单独编码。

运行默认设计生成器：

```powershell
.\.venv\Scripts\python.exe scripts\generate_design.py
```

它只生成参数设计和 manifest，不启动 FEM。后续批量求解器应读取 `outputs/designs/default/cases/*.json`，每个 case 独立写结果，失败样本保留状态，不中断整个批次。

固定场景由 configs/scenario_suite.json 定义，覆盖低温高湿慢风、热干高速、大小尺寸与初始含水率、内部扩散上下限、加密网格、长时过程，以及未来 prescribed/ALE 收缩候选。它们标记为 fixed_verification，与随机训练设计分开保存。

生成固定场景：

    .\.venv\Scripts\python.exe scripts\generate_scenarios.py
