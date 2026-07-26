# Olise CRT Photo Skill

一套面向不同照片场景自适应的冷青 CRT / VHS / 摄录机风格化 Skill。核心不是单纯叠蓝色 LUT，而是模拟“镜头重新拍摄旧电视屏幕”的完整视觉链路。

## 场景处理总结

| 场景 | 处理方式 | 关键保护 |
|---|---|---|
| 静态人像、合照、自拍、物品 | 最轻鱼眼，不加拖影，保留较细的屏幕纹理 | 保留人物辨识度，肤色只偏冷、不变紫 |
| 低清截图、转载图 | 自动降低像素化、柔化和栅格强度 | UI 文字和主体轮廓不被二次糊掉 |
| 行走、手势、轻动态抓拍 | 中等边缘鱼眼与极短荧光余辉 | 有动态感，但不制造马赛克式重影 |
| 足球、篮球、跳跃等强动态 | 短帧持续、隔行场梳齿、场同步滑移和更明显的 RGB 荧光栅格 | 主体仍可辨认，不合成长距离复制拖影 |
| 暖黄室内、钨丝灯环境 | 先做自适应白平衡，再施加冷青偏色 | 避免暖底与蓝色相加后变脏 |
| 紫粉 LED、直播美颜光 | 洋红收敛为冷灰 | 避免鼻尖、脸颊出现紫色斑块 |
| 红绿黄青同时出现 | 按色相族选择性映射 | 红压暗、绿抽灰、黄变脏、青蓝存活 |

所有场景都会得到分辨率自适应柔化、纵向 RGB 荧光栅格、横向扫描线、轻微 CRT 黑边、曝光自适应光晕和统一的冷青屏幕基调。梦核层由青白荧光晕、轻微色度渗色、低频青绿漂移、滚动曝光带与细颗粒共同构成，不使用整张图统一发紫的色罩。

处理器保留原始尺寸与构图，不自动裁成 4:3。动态场景的差异主要来自旧电视的场扫描和短暂荧光余辉，而不是普通软件运动模糊。

## 对比

![四类场景效果总览](docs/assets/comparisons/00-comparison-overview.jpg)

### 强动态球场

强动态使用短暂且连续的 CRT 余辉，并强化纵向 RGB 荧光栅格、红青通道错位、滚动场同步滑移和轻微隔行梳齿。人物、球和看台仍可辨认，不生成数个清晰复制的主体。

![强动态球场对比](docs/assets/comparisons/01-sports-action.jpg)

### 暖光人像

先校正暖光污染，再进入冷青环境，同时保护肤色。

![暖光人像对比](docs/assets/comparisons/02-warm-portrait.jpg)

### 红、黄、青色块

红色变暗变密，黄色失去数码荧光感，青色成为主要存活色。

![色相族对比](docs/assets/comparisons/03-color-poster.jpg)

### 红色草莓与绿色叶片

红色保留身份但更暗，绿色明显抽灰，而不是整张图统一降饱和。

![红绿食物对比](docs/assets/comparisons/04-red-green-food.jpg)

## 使用

Skill 位于 [`apply-olise-crt`](apply-olise-crt/)。

```bash
python3 -m pip install -r apply-olise-crt/scripts/requirements.txt
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output
```

批量处理：

```bash
python3 apply-olise-crt/scripts/apply_olise_crt.py a.jpg b.png -o output
```

自动识别之外，也可手动指定场景尺度：

```bash
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output --motion static
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output --motion mild
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output --motion sports
```

动态与梦核感可以分开调节，不会改变核心色彩映射：

```bash
# 只调整短暂 CRT 余辉；范围 0.0–2.0，默认 1.0
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output \
  --motion sports --motion-strength 1.25

# 只调整青白光晕与屏幕信号漂移；范围 0.0–1.5，默认 0.55
python3 apply-olise-crt/scripts/apply_olise_crt.py photo.jpg -o output \
  --dream-strength 0.70
```

建议先使用默认值。体育照片如果仍显得太“数码清晰”，优先小幅增加 `--motion-strength`；如果只是想更像拍摄旧电视、但不希望主体更糊，优先增加 `--dream-strength`。

在 Codex 中可直接调用：

```text
我想制作 Olise/奥利塞同款失真照片。
```
