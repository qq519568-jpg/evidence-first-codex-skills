# 执行端 Blender 5.2 实战坑（跨项目复用，2026-08-13 S02 实测）

> 用途：Blender执行端写 bpy 前的定点检索清单。全部来自真实渲染事故，每条=事故现象+根因+正确写法；本文件是技能域正本，不依赖旧项目AGENTS记录。

## 目录

- 材质与渲染
- 动画与相机
- 场景与输出
- BL_ShotLab与TC_01—TC_04压测新增坑
- 迁移事故与二进制安全

## 一、材质与渲染

1. **载入网格材质槽赋值失效**：`mesh.materials[0] = mat` 对 blend 载入后的网格在渲染层不生效（数据层正确、渲染层仍是旧材质——S02 整帧渲成面罩黄的真凶）。**必须 `materials.clear()` + `materials.append(mat)`**。且渲染会话内一律新建材质，禁止读载入材质的节点值（载入材质节点树有腐化风险）。

2. **0 用户材质存盘被清除**：只建不赋给物体的材质（标注变体等）保存 .blend 时直接消失——要么 `use_fake_user=True`，要么渲染会话内重建。

3. **灰材质+灯光=隐形，emission=可见**：白膜静帧/MP4 用"自发光灰"（Emission 0.5-1.0 灰）替代灯光照明，全发光渲染，别依赖灯光系统。

4. **缩放覆盖炸弹**：`box()` 用 `obj.scale=尺寸` 建体后，再赋值 `obj.scale=(2,2,2)` 会**覆盖**原尺寸（S02：8cm 面罩变 2m 立方体糊在镜头前挡全世界）。改尺寸必须用旧值相乘（`obj.scale *= 2`），禁止覆盖赋值。

5. **掩码/纯色渲染必须 `scene.view_settings.view_transform = 'Standard'`**：AgX 会把纯蓝压成 (20,86,209)，导致像素断言误报。注意：该设置在某些场景下会被世界色动画等覆盖，标注渲染前先清世界色动画。

6. **Render Result 探针无效**：5.2 后台 `bpy.ops.render.render()` 后 `bpy.data.images['Render Result'].size=[0,0]` 但 `write_still=True` 输出 PNG 正常——验收看 PNG 像素，不要用 RR 缓冲判失败。

## 二、动画与相机

7. **相机朝向 K 帧反转疑点**：`v.to_track_quat('-Z',up).to_euler()` 直接键 rotation_euler，机位相机渲染时朝向反转（实测 fwd=反方向）；正交鸟瞰相机同公式正常。根因未定，规避：相机加 TRACK_TO 约束指向 key 了位置的注视空物体，euler 不键帧。

8. **关键帧读写走分层 Action**：5.2 中 fcurves 在 `action.layers[].strips[].channelbags[].fcurves`，不在 `action.fcurves`。取插值点要遍历分层结构；`keyframe_insert` 正常可用，改 easing 需按分层路径找到 fcurve 再改 `keyframe_points`。

9. **节点输入动画**：`node_input.keyframe_insert('default_value', frame=f)` 可用于世界色/材质发射强度，作用域限定在该 node_tree（实测不会串材），重载后正常评估。

## 三、场景与输出

10. **临时对象删除必须打标记**：渲染循环里清理临时对象（航迹线/文字/箭头）不能按"材质名前缀"判删——标注渲染后场景物体全带 RE_ 前缀，会误删全部场景几何（S02 静帧全空真凶）。创建时 `obj['annot']=True`，按标记删。

11. **删除对象先解绑集合**：`bpy.data.objects.remove(obj, do_unlink=False)` 会因场景集合还引用而报错；先 `for coll in obj.users_collection: coll.objects.unlink(obj)` 再 remove，避免 do_unlink=True 连坐删除共享材质。

12. **VSE 无头模式序列检测失效**：`strips.new_image()` 只加载首帧（elements==1），合成 MP4 会变 240 帧同一张图——**MP4 一律用 3D 直接渲染（`image_settings.media_type='VIDEO'` + FFMPEG/H264）**，VSE 只用于剪辑。

13. **5.2 工厂设置无默认 World**：`bpy.data.worlds` 可能为空，`worlds.get("World")` 返回 None——先 `worlds[0] if worlds else worlds.new("World")`，再 `scene.world = world`。

14. **父子绑定继承缩放会压扁子物体**：武器等锚点物禁止 parent 到缩放过的角色体块，改世界坐标独立关键帧；需 parent 时用无缩放的 Empty 做父。

15. **bpy.ops 建对象已自动入集合**：`bpy.ops.mesh.primitive_*` 创建的对象已在活动集合，不要再 `scene.collection.objects.link()`（会报重复）；手动 `bpy.data.objects.new` 的对象才需要 link。

## 2026-08-14 BL_ShotLab Stage0/1 新增坑（镜头实验室实弹验证）
- 视频输出 API 顺序（5.2 实测）：必须先 image_settings.media_type='VIDEO' 再 file_format='FFMPEG'——file_format 静态枚举里有 FFMPEG，但 media_type=IMAGE 时赋值报 enum not found。旧笔记顺序反的。
- world.use_nodes 载入即真：build 会话设 use_nodes=False 存盘，open_mainfile 读回后 use_nodes=True——此后 world.color= 赋值彻底失效（背景恒 0.05 真凶）。改背景必须编辑 Background 节点 Color。
- EEVEE View Z Depth 返回正值（非负值）：MapRange 用 From Min=0.5 / From Max=50 / To Min=1 / To Max=0（近白远黑）。负值假设会全场白 mean 235。
- 深度通道天空黑场：天空像素走 world 背景不走进材质覆盖——深度渲染前必须把 Background 节点压纯黑，否则 min 永远=背景色，黑场断言必挂。
- ffmpeg 9.0 删除 -vsync；mingw 版 ffmpeg 会把参数里的逗号拆成两个 argv（select=eq(n,2) 报 No such filter）——抽帧用 -ss 定点两次调用，禁用 select 滤镜。
- Windows python subprocess 调 ffmpeg：text=True 默认 GBK 解码 UTF-8 输出会崩 reader 线程——必须 encoding='utf-8', errors='replace'；输出目录用 ASCII 路径。
- opencode 的 blender 工具会坏：今天 JS 包装层报 require is not defined 全不执行——检测到异常立即退回 bash 直调 blender.exe --background --python，别重试。
- 武器白分场景规则：武器 emission 白只用于武器为主体的近景（CU/ECU）；宽景别（VWS/FS/MLS/MS）检查版武器必须 0.45 灰——武器白会把刀-盾-人粘成单连通域，blob 计数 2->1 崩坏。
- 远景 blob 过滤：20%-最大块规则只用于近景；17m 外群像采样块 300-6000px 会被误杀——远景用绝对阈值（本次 >=300 采样px@step2）。
- 竖屏近景构图规律：人形 1.9m 高纵向塞满画幅——MCU/CU 机位必须拉到画幅高度 > 人高 1.5 倍才有灰背景，否则 char% 冲 80+ 超带。竖屏 MS 档用 30mm/4.7m，35mm 会超带。
- 竖屏 EWS 群像几何：24mm 下 7 体 4m 圈需要 17m+ 机位距离；30m 场地地理+群像同框竖屏不可兼得——EWS 拆两帧（地理空镜+群像）。
- 扁平白板的 ECU 构图：正对满窗=100% 白必超带；贴边构图或 ~78 度掠视压缩面宽才能落 50-80 带。
- 投影断言点支持：细长武器原点常在画外而刀身入画——断言函数必须同时支持物体名和显式世界坐标点。
- 入画方位角：要用投影到视轴后的水平角判断，直接 atan(dx/dy) 会算错（山君在 VWS 实际合法入画，初算判出框）。

## 2026-08-14 压测套件 TC_01_NarrowOrbit 新增坑（高频压测第一案）
- **断言按秒分段，不按帧号**：遮挡状态的角色（如 frame1 被墙挡住的哨兵）本就不该要求入画——投影断言要带时间门槛（`sentry_from_t`），t 之前只查 scout。慢放/变速通道（50% 慢放 288 帧）里"帧 48"只对应 t=0.98s，断言门槛必须统一换算成秒。
- **长道具桥接连通域**：2.2m 长枪立在双主体之间，枪身把两个 blob 粘成 1（blob_count 2→1）。解法：道具挪到远离另一主体的侧位，且让它在断言帧被前景墙遮挡（遮挡既断桥又合叙事）。blob 分离判定要看屏幕 x 分离 >0.3m（约 15% 半宽）+ z 层差。
- **char% 校准法**：35mm 竖屏 hFOV 半宽仅 10.9°，char% 差 1-2 个点时不要动相机路径（spec 硬数据）——整簇场景向相机路径收近 0.8m 即 +2.6pct。**hero_screen_y 偏上（0.318）→ 抬注视点 Z（1.42→1.75）落 0.443**；注意抬高注视点会压低终帧主体，留 0.7-0.85 带即安全。
- **write_still 不替换 `####` 占位符**：filepath 带 #### 时逐帧 write_still 全部写到同一个字面名文件、后帧覆盖前帧（Blender 日志里显示的 Saved 路径就是字面名）。必须循环内逐帧显式拼 `%04d` 文件名。
- **Blender 内读图自检会崩**：5.2 后台 `bpy.data.images.load` + `pixels` + `remove` 循环触发 EXCEPTION_ACCESS_VIOLATION（写 crash.txt）。像素自检一律走系统 Python（PIL+numpy 读 PNG），Blender 只负责渲染。
- **公共模块顶部必须显式 `import bpy`**：材质构建等模块级函数若只靠函数内 import bpy，第一个调用点会 NameError（模块 import 时顶层没有 bpy 绑定）。
- **H264 平灰画面压得极小**：白膜 MP4 144 帧仅 0.19MB 属正常（平色 H264 高效），验收 MP4 必须 ffprobe 查 nb_read_frames/duration，别凭体积判断。

## 2026-08-14 迁移事故：递归文本替换毁掉二进制（血泪级）
- **事故模式**：为把`<LegacyAssetRoot>`路径引用改成`<ProductionRoot>`，对资产树做无差别文本递归替换。两个坑叠加：
  1) PS5.1 的 -Include 与 -LiteralPath 组合静默失效（不报错不过滤），实际上遍历了全部 2326 个文件；
  2) **Blender 写的 PNG 内嵌路径元数据**（含旧路径字符串），匹配后被当文本重写——0x89 魔数变成 EF-BF-BD 替换字符，1906/2092 张 PNG 报废；.blend 也含 scene.render.filepath 字符串，全部被毁；MP4 无路径元数据幸免。
- **铁律**：资产树内永远只对白名单扩展名（*.py/*.md/*.txt/*.yaml/*.json）做文本替换，且用 -filter 逐扩展名或先 Get-ChildItem 过滤再操作；二进制文件一律不动。批量替换前先 dry-run 打印命中清单。
- **教训2**：任何大动作前先自检命令的实际行为（PS5.1 -Include 组合有已知坑），别相信直觉。
- **可恢复性**：白膜管线所有 PNG 均可从 previs\scripts 重建（build/render 脚本留档的意义在此）；.blend 同理。脚本是唯一真源，渲染图是衍生品。

## 2026-08-14 BL_ShotLab Stage2/3 新坑（机位运动+纵深实测）
- PNG 序列渲染：5.2 里 filepath 含 %04d + render(animation=True) 会把 %04d 当字面量，输出 f%04d.png0001.png——序列一律逐帧 frame_set+write_still。
- 断言场景适配铁律：贴脸全白帧 char%=100 是正确行为；中带断言只配用于画面含地面的帧；自检引用的静帧号必须与渲染静帧集一致。
- T3_01 纵深交叉的 blob 过滤：前+后景双主体用相对 20% 规则（绝对 300px 阈值会把 837px 的中等碎片算成第三 blob）。
- 希区柯克变焦数学：主体比例恒定 充要条件是 d/L 恒比（相机距离/焦距），YAML 给的两组端点若违背此比，char% 必漂移——执行端要主动校验并声明偏差。
- 三平面纵深（2/6/12m）多人同框：竖屏 24mm 只 37 度 HFOV，近者 2m 处占屏 47%，会把背后角色遮死——平面错开方案：近者居中偏右、中者左 1.5m、远者左 1.0m，三 bearing 分离。
- 穿越相机平面的跑步角色：车道必须偏离相机 0.8m+（身体半径+余量），否则角色穿过相机位置黑帧。

## 2026-08-14 BL_ShotLab Stage4/5 重大坑（多人调度+时间调度实测）
- **Blender 5.2 parent 赋值行为变更（最高优先级坑）**：4.x 的 obj.parent=p 保持子物体世界位置不变（自动换算 local）；5.2 直接把原 transform 当 local——子世界 = 父世界 + 旧世界值（双重叠加）。建场时世界坐标创建再 parent 的 nose_cube，角色一挪位鼻子就飞天上。铁律：parent 后必须显式写 child.location=期望local + matrix_world 断言验证（build 脚本已内置断言）。
- **time_remap 工具已验证**（S5_01/S5_02）：5.2 分层 action 的 fcurve 可 evaluate(t) 采样→重 bake 逐帧 keyframe→实现任意映射（1x/0.25x/0x/2x 多轨解耦+顿帧）。做法：collect fcurves→mapping(f) 采样→animation_data_clear→逐帧 keyframe_insert→全部 LINEAR。
- 整帧 diff 断言在多主体画面会把别的角色动作算进来——单轨验证必须逐角色掩码 diff。
- 慢动作段帧差阈值要按倍率缩放（0.25x 段阈值 0.05 不是 0.5）。
- 掩码口径：中距离多主体掩码用 20% 相对过滤；绝对 300px 阈值会卡住 316px 的鼻子级碎片。
- RGB 纯色掩码纯度实测：EEVEE 硬边几何混合像素仅 0.14-0.20%（AA 边缘），<3% 断言稳定可过；Standard 色彩变换必须开（AgX 会压纯色）。

## 四、2026-08-14 TC_02 压测新增（俯冲+dolly-zoom 实测）

16. **5.2 渲染投影规律 ≠ 教科书**：实测（EEVEE/CYCLES 同）tan(半垂直FOV)=24/f_keyed（等效焦距=键入值一半）、tan(半水平FOV)=tan(半垂直)×(res_x/res_y)——**36mm 传感器宽度被完全忽略**，水平视野按"垂直FOV×画幅比"推导。`world_to_camera_view`/`view_frame` 与渲染结果不一致（它们用标准 12/f + 方形传感器），**渲染前投影断言必须自算**：x_ndc=0.5+local.x/(depth×2×tan_h)，tan_h=24/f×(res_x/res_y)，tan_v=24/f。此规律影响一切 char%/构图计算。

17. **keyframe_insert 重复点炸弹**：对已有关键帧的帧位再次 keyframe_insert 会新增重复点，求值取旧值——校准/迭代改值必须直接改 fcurve.keyframe_points[i].co[1]，禁止重复 insert。

18. **CameraData/TexCoord 深度链路已废**：ShaderNodeCameraData（View Z Depth/View Distance）、TexCoord.Camera.Z、Geometry.Position+VectorMath.DISTANCE 在 5.2 无头渲染下输出常数或不可信值（EEVEE/CYCLES 实测）。**深度 pass 可靠替代=瓦片恒定灰度法**：地面切 N×N 瓦片+逐物体材质，发射灰=(距离-0.1)/clip_far，逐帧注入相机坐标算距离——恒定材质是唯一 100% 可信路径。

19. **TextCurve 无 .type 属性**：5.2 清理字体曲线按 users==0 删，判 d.type=="FONT" 会 AttributeError。

20. **ShaderNodeVector 不存在**：向量常量节点在 5.2 不可用（报"尚未定义节点类型"），改用 ShaderNodeCombineXYZ 三通道注入。

21. **低机位仰拍大主体像素质心定律**：相机低于主体中腰时，近端部位(腿)像素放大、远端(头)缩小，质心天然下沉且调注视点无法修正（存在全局最小值）——hero_screen_y 带不过时**抬相机到主体中腰**，不是调 track。

22. **跨盘转移二进制必须二进制模式**（流程坑非 Blender）：文本模式转移会把 PNG/MP4 的 0x89 等字节静默替换为 U+FFFD，文件"能看不能开"。转移后用头字节校验；生产管线依赖脚本留档+可重建性（TC_01/TC_02 均因脚本全留档无损重建）。注意：5.2 blend 文件头为 28b52ffd（新压缩格式，非 BLENDER 也非 gzip），别当损坏。。

## 2026-08-14 BL_ShotLab Stage6/7 新坑（特效代理+毕业考收官）
- 5.2 相机 keyframe 双挂载：相机物体与 data 共享同一 action（location 和 lens 曲线两层都可见）——time_remap 只扫物体层收集，重插 lens 走 cam.data.keyframe_insert、其余走 obj.keyframe_insert；clear 必须两层都清，否则旧 action 残留。
- RGB 分色渲染后必须恢复主体材质：红/绿材质亮度通道只有 76，后续灰白自检阈值 217 会全 0——渲染完立即 materials.clear()+append(原材质)。
- 60 度俯角地面窗口几何：半视场 13.5 度时画面只覆盖相机底座前方 2.7-8.6m 地面——站位先算窗口再摆人；俯角下人形压成脚印 char% 仅 1-2%，要 5-10% 锚点必须抬高台（实测 2.35m 台=5.0%）。
- 巨兽横向体长横贯画面（169% 画面宽）必与人粘连——转 90 度让体长沿纵深，俯角自然压缩（实测 46.3% 入带）。
- 交叉帧 char% 天然下陷，dolly zoom 恒比断言取首尾帧（实测漂移 0.0%）而非中段。
- VFX 代理与主体头部 0.05m 间隙也会连通域粘连——代理件与主体至少 0.4m 屏幕间距。
- 扁平代理的深度是均匀的（std 0.6 正常），深度断言用 mean 范围+黑洞率，别用 std>3。
- 深度图自检前必须 .convert('L')，RGB 模式取像素是 tuple 会炸。
## 2026-08-14 TC_04 批次4 压测新坑（Stage6 特效七连测 + Stage7 毕业考）
- 23. **投影口径正本**：5.2 实测 tan(半垂直FOV)=sensor_h/(2f)=12/lens（36mm 传感器被忽略，tan(半水平)=tan_v×(res_x/res_y)）。TC_02 记录的 24/f 有 2x 误差——char% 断言/构图自算一律用 12/lens，禁用 world_to_camera_view。
- 24. **TRACK_TO 俯角>10° 翻转失效**：track 低于相机过多时，约束解出错误分支（背向渲染），画面全黑或背离主体。规避：track z 保持在主体中高、俯角≤5-8°；构图用相机距离控制而非俯角。
- 25. **TRACK_TO 重载随机翻转/背向**（S02 反转疑点升级）：blend 保存重载后渲染随机上下翻转或背向，重新约束/手工矩阵均不能可靠修复。规避铁律：渲染必须与构建同会话；跨会话只做文件校验（PIL 读 PNG），不重渲。
- 26. **动画 hide_render 掩码隐藏失效**：有 hide_render 关键帧的物体（dome 等），渲染掩码前直接赋 hide_render=True 会被动画求值覆盖回 False——半透 dome 变不透明黑墙吞掉背后主体（char% 虚低 2-4 倍）。规避：临时摘 action（obj.animation_data.action=None）再隐藏，渲后还原。
- 27. **freeze 反向冻结**：命中帧设 CONSTANT 会让前段插值段也冻结（CONSTANT 由段右侧键决定）。规避：freeze 前在 hit-1 插普通键收尾前段运动。
- 28. **多层动画跨镜头插值污染**：同通道上一镜末帧与下一镜关键帧间会插值（如 yaw 1.57@1 → 0@61 使 1-60 全段旋转）。规避：每个镜头边界帧补相同值键（kp@60=同值）。
