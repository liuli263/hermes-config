---
name: adc-ai-design-platform
description: 自动化操作 adc.acsbim.com:7002（Agile Design Cloud）—— 登录、进入项目、导航到 AI 生图、触发生成并提取结果图片。
version: 1.0.0
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

6. **页面内“下载图片”按钮可点击做站内验证，但交付给用户时，最稳妥的是把结果图 URL 直接下载到本地。**
   - 用 Python `requests.get()` 保存为本地 PNG/JPG
   - 再通过 `MEDIA:/absolute/path` 回传到微信/聊天平台

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
11. 下载到本地
12. 回传图片给用户

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

## 下载结果图示例
```python
import requests
url = '<result-image-url>'
out = '/tmp/adc-ai-gen-result.png'
r = requests.get(url, timeout=60)
r.raise_for_status()
open(out, 'wb').write(r.content)
print(out)
```

## 常见坑
- 点击项目名称不跳转：改点项目封面图
- 以为必须打开预览弹窗才能下载：实际上结果图 `src` 已足够
- SPA 页面切换后 snapshot 没及时刷新：要主动重新取 `browser_snapshot(full=true)`
- 只靠视觉判断页面状态：优先结合 `document.body.innerText` 和 `location.href`

## 验证标准
- URL 已进入 `#/adcHome/genImg?...`
- 页面出现 `开始创作`
- 点击后先出现 `生成中...`
- 完成后出现 `下载图片`
- 能拿到结果图 URL
- 本地已成功保存图片文件
- 已通过 `MEDIA:` 回传给用户
