---
name: adc-ai-design-platform
description: 自动化操作 adc.acsbim.com:7002（Agile Design Cloud）—— 登录、进入项目、导航到 AI 生图、触发生成并提取结果图片。
version: 1.1.1
metadata:
  hermes:
    tags: [browser, adc, wechat, image-generation, vue-spa]
    related_skills: [dogfood]
---

# ADC AI Design Platform Automation

适用于站点：`https://adc.acsbim.com:7002/`

## 何时使用
- 用户要求在 ADC 平台里执行固定业务流程
- 需要进入“项目空间”中的某个项目并继续操作左侧菜单
- 需要在“AI绘图 → AI生图”里生成图片并下载结果
- 需要把 ADC 生成结果可靠地回传到微信或其他平台

## 关键经验
1. **项目空间中，进入项目优先点击项目封面图，不要优先点项目名称文字。**
   - 在“创意产业园”等项目卡片里，文字本身经常不是实际跳转热点。
   - 更稳定的方法：在 DOM 中找到 `img.masonry-img[alt="项目名"]`，对图片元素派发完整鼠标事件序列（`mouseover` → `mousedown` → `mouseup` → `click`）。

2. **这是 Vue SPA，切页后要用 `browser_snapshot(full=true)` + `browser_console(expression=...)` 双重确认。**
   - 重点看：
     - `location.href`
     - `document.body.innerText`
     - 左侧菜单是否已展开
     - 目标按钮是否真实出现

3. **AI绘图菜单需要先展开，再点击子菜单 `AI生图`。**
   - 常见路径：左侧 `AI绘图` 展开后，会出现 `AI生图 / AI渲染 / 一键生成方案 ...`

4. **AI生图任务启动后，要轮询页面文本而不是盲等。**
   - 点击 `开始创作` 后，用 `browser_console(expression=...)` 检查：
     - 是否出现 `生成中...`
     - 是否出现 `下载图片`
     - 是否出现结果图 `img[alt*="创作结果"]`

5. **结果图出现后，不必执着于预览弹窗。**
   - 即使用户口头说“点击中间图片成果展示区，下载弹出的图片”，实际完成任务时：
     - 可先尝试点击结果图区/结果图本身；
     - 但如果预览层没有真正显示，或者页面已经直接暴露结果图 URL，**直接下载当前结果图 `src` 即可**。
   - 该站点中结果图区图片通常可从：
     - `img[alt*="创作结果"]`
     - 或带 `compare-image` 类名的图片元素
     直接拿到 `src`。

6. **下载后一定要校验真实文件格式，不要只信扩展名或响应头。**
   - 该站点曾出现：URL/响应头看起来像 `png`，但实际字节内容是 `JPEG`。
   - 因此下载脚本应按文件头（magic bytes）识别真实格式，再决定保存后缀。
   - 技能包附带脚本：`scripts/adc_ai_gen_flow.py`

7. **如果目标是发回微信，不要把 `MEDIA:/path` 文本本身当成“已成功发图”。**
   - 之前真实踩坑：聊天回复中出现 `MEDIA:/tmp/...`，但用户侧并没有真正收到微信原生图片消息。
   - 对微信交付，要以“用户客户端实际收到”为完成标准。
   - 在 Hermes/Weixin 链路里，优先走 Weixin 原生直发，而不是仅输出 `MEDIA:` 文本。

## 推荐流程
1. 打开登录页
2. 输入账号密码并登录
3. 进入“项目空间”
4. 找到目标项目名
5. 点击项目封面图进入项目
6. 展开左侧 `AI绘图`
7. 点击 `AI生图`
8. 点击 `开始创作`
9. 轮询直到出现结果图 / `下载图片`
10. 提取结果图 `src`
11. 使用技能附带脚本 `scripts/adc_ai_gen_flow.py` 下载并按真实文件头修正后缀
12. 若需要发微信，优先走 Weixin 原生直发
13. 只有用户客户端真正收到图片，才算完成

## DOM / 状态检查示例
### 查找项目封面图
```js
[...document.querySelectorAll('img.masonry-img')]
  .find(el => (el.getAttribute('alt') || '').trim() === '创意产业园')
```

### 对项目封面派发点击事件
```js
const img = [...document.querySelectorAll('img.masonry-img')]
  .find(el => (el.getAttribute('alt') || '').trim() === '创意产业园');
['mouseover','mousedown','mouseup','click'].forEach(type =>
  img.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }))
);
```

### 检查 AI 生图状态
```js
({
  href: location.href,
  body: document.body.innerText.slice(0, 4000),
  imgs: [...document.querySelectorAll('img')].map(i => ({ alt: i.alt || '', src: i.src }))
})
```

### 提取结果图
```js
const img = [...document.querySelectorAll('img')]
  .find(i => (i.alt || '').includes('创作结果'));
img ? img.src : null;
```

## Python 辅助脚本
技能包附带：`scripts/adc_ai_gen_flow.py`

用途：
- 下载 ADC 结果图 URL
- 按真实文件头判断扩展名（jpg/png/gif/webp）
- 输出最终保存路径，便于后续微信发送

示例：
```bash
python3 ~/.hermes/skills/browser-automation/adc-ai-design-platform/scripts/adc_ai_gen_flow.py \
  'https://example.com/result-image-url'
```

## 常见坑
- 点击项目名称不跳转：改点项目封面图
- 以为必须打开预览弹窗才能下载：实际上结果图 `src` 已足够
- SPA 页面切换后 snapshot 没及时刷新：要主动重新取 `browser_snapshot(full=true)`
- 只靠视觉判断页面状态：优先结合 `document.body.innerText` 和 `location.href`
- 把 `.png` 扩展名或响应头当成真实格式：要按文件头识别
- 把 `MEDIA:/path` 当成微信必然送达：不可靠，微信回传要优先走原生直发

## 验证标准
- URL 已进入 `#/adcHome/genImg?...`
- 页面出现 `开始创作`
- 点击后先出现 `生成中...`
- 完成后出现 `下载图片`
- 能拿到结果图 URL
- 本地已成功保存图片文件
- 如需发微信，接口返回成功且用户客户端实际收到图片
