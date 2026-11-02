# 指标清单

下表由 `healthkit_report/metrics.py` 生成。`HKQuantityTypeIdentifier` 前缀已省略。

| key | 中文名 | HealthKit 类型 | 单位 | 聚合 |
|---|---|---|---|---|
| `steps` | 步数 | `StepCount` | count | 累加 |
| `walk_dist` | 步行+跑步距离 | `DistanceWalkingRunning` | km | 累加 |
| `cycle_dist` | 骑行距离 | `DistanceCycling` | km | 累加 |
| `active_energy` | 活动能量 | `ActiveEnergyBurned` | kcal | 累加 |
| `basal_energy` | 静息能量 | `BasalEnergyBurned` | kcal | 累加 |
| `flights` | 爬楼层数 | `FlightsClimbed` | count | 累加 |
| `exercise_min` | 锻炼时间 | `AppleExerciseTime` | min | 累加 |
| `stand_min` | 站立时间 | `AppleStandTime` | min | 累加 |
| `daylight_min` | 日照时间 | `TimeInDaylight` | min | 累加 |
| `hr` | 心率 | `HeartRate` | bpm | 均值 |
| `resting_hr` | 静息心率 | `RestingHeartRate` | bpm | 均值 |
| `walking_hr` | 步行平均心率 | `WalkingHeartRateAverage` | bpm | 均值 |
| `hrv` | HRV (SDNN) | `HeartRateVariabilitySDNN` | ms | 均值 |
| `hr_recovery` | 心率恢复 | `HeartRateRecoveryOneMinute` | bpm | 均值 |
| `resp_rate` | 呼吸频率 | `RespiratoryRate` | breaths/min | 均值 |
| `spo2` | 血氧饱和度 | `OxygenSaturation` | % | 均值 |
| `weight` | 体重 | `BodyMass` | kg | 均值 |
| `height` | 身高 | `Height` | cm | 均值 |
| `bmi` | BMI | `BodyMassIndex` | kg/m2 | 均值 |
| `vo2max` | 最大摄氧量 | `VO2Max` | mL/min/kg | 均值 |
| `wrist_temp` | 手腕温度 | `AppleSleepingWristTemperature` | degC | 均值 |
| `breath_disturb` | 睡眠呼吸紊乱 | `AppleSleepingBreathingDisturbances` | count | 均值 |
| `walk_speed` | 步行速度 | `WalkingSpeed` | km/h | 均值 |
| `step_len` | 步长 | `WalkingStepLength` | cm | 均值 |
| `dbl_support` | 双支撑占比 | `WalkingDoubleSupportPercentage` | % | 均值 |
| `asymmetry` | 步行不对称 | `WalkingAsymmetryPercentage` | % | 均值 |
| `steadiness` | 步行稳定性 | `AppleWalkingSteadiness` | % | 均值 |
| `env_audio` | 环境音量 | `EnvironmentalAudioExposure` | dB | 均值 |
| `hp_audio` | 耳机音量 | `HeadphoneAudioExposure` | dB | 均值 |
| `run_speed` | 跑步速度 | `RunningSpeed` | km/h | 均值 |
| `run_power` | 跑步功率 | `RunningPower` | W | 均值 |
| `run_stride` | 跑步步幅 | `RunningStrideLength` | m | 均值 |
| `run_vert_osc` | 垂直振幅 | `RunningVerticalOscillation` | cm | 均值 |
| `run_gct` | 触地时间 | `RunningGroundContactTime` | ms | 均值 |

## 睡眠

`HKCategoryTypeIdentifierSleepAnalysis` 被拆成四个派生指标：

| key | 含义 |
|---|---|
| `sleep_h` | 总睡眠（Core + Deep + REM） |
| `core_h` | 核心睡眠 |
| `deep_h` | 深睡 |
| `rem_h` | REM |

`InBed` 与 `Awake` 分别记录为 `inbed` / `awake`。睡眠按**醒来日期**归档，
同一晚若多个来源都有记录，取优先级最高且睡眠时长最长的一份。

## 派生指标

| key | 计算方式 |
|---|---|
| `bmi` | 体重 / 身高²（若无 BMI 记录） |
| `deep_share` / `rem_share` | 深睡、REM 占总睡眠比例 |
| `audio_exposure` | 从 1 dB 分桶的时长直方图汇总 ≥80 dB / ≥90 dB 时长 |
| `run_pace` | 跑步总时长 / 总距离（min/km） |
| `run_cadence` | 步数 / 时长（步/分） |

## 单位归一化

| 原始单位 | 归一化为 | 说明 |
|---|---|---|
| `Cal`、`kcal` | kcal | Apple 的 `Cal` 就是千卡 |
| `mi` | km | × 1.609344 |
| `hr` | min | × 60 |
| `lb` | kg | × 0.45359237 |
| `%`（值为 0–1） | %（0–100） | 血氧、双支撑、不对称、稳定性等 |
