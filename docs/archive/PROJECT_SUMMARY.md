# BitBrowser 自动化 Demo 项目

## 项目概述

本项目是 BitBrowser（比特浏览器）本地 API 的 Python 调用示例，演示如何通过 BitBrowser 本地服务接口进行浏览器窗口的创建、管理，并结合 Selenium 和 Playwright 进行自动化操作。

## 项目结构

```
python-demo/
├── bit_api.py          # BitBrowser 本地 API 封装
├── bit_selenium.py     # Selenium 自动化示例
├── bit_playwright.py   # Playwright 自动化示例
```

## 模块说明

### bit_api.py

BitBrowser 本地 API 的核心封装，基于 `requests` 库，与运行在 `http://127.0.0.1:54345` 的 BitBrowser 本地服务通信。提供以下功能：

| 函数 | 功能 |
|------|------|
| `createBrowser()` | 创建浏览器窗口，支持配置名称、代理方式、指纹参数等 |
| `updateBrowser()` | 批量更新浏览器窗口属性（如备注等） |
| `openBrowser(id)` | 打开指定浏览器窗口，返回调试连接地址（ws/http） |
| `closeBrowser(id)` | 关闭指定浏览器窗口 |
| `deleteBrowser(id)` | 删除指定浏览器窗口 |

参考文档：https://doc2.bitbrowser.cn/jiekou/liu-lan-qi-jie-kou.html

---

## 浏览器窗口接口文档

> 来源：https://doc2.bitbrowser.cn/jiekou/liu-lan-qi-jie-kou.html

### 通用约定

- 所有接口请求 Method 均为 **POST**，传参方式为 body 传参（JSON 格式），非 form-data 也非 url 参数
- 返回 JSON 对象中 `success: true` 表示成功，数据附加在 `data` 对象中
- 返回 `success: false` 表示失败，失败信息附加在 `msg` 中

```json
// 成功示例
{ "success": true, "data": { "id": "xxx", "groupName": "xxx" } }

// 失败示例
{ "success": false, "msg": "分组id必传" }
```

---

### 1. 健康检查

**POST** `/health`

无参数，用于测试 Local Server 是否连接成功。

```json
{ "success": true }
```

---

### 2. 创建浏览器窗口

**POST** `/browser/update`

- `browserFingerPrint` 指纹对象必传，传空对象 `{}` 即可随机生成指纹
- 未指定 `groupId` 时，系统会默认创建 API 分组并分配窗口
- win7/win8/win server 2012 不支持 109+ 内核，需指定 `coreVersion` 为 104
- win8 以下不支持 Firefox 内核

#### 请求参数

| 名称 | 类型 | 必选 | 说明 |
|------|------|------|------|
| groupId | string | 是 | 分组 ID，不传则自动创建 API 分组 |
| name | string | 否 | 窗口名称 |
| platform | string | 否 | 账号平台 URL |
| url | string | 否 | 额外打开的 URL，多个用逗号分隔 |
| remark | string | 否 | 备注信息 |
| userName | string | 否 | 平台账号用户名（自动填充） |
| password | string | 否 | 平台账号密码（自动填充） |
| isSynOpen | number | 否 | 多开设置：1 允许 / 0 禁止 |
| faSecretKey | string | 否 | 2FA 密钥的 SecretKey |
| cookie | string | 否 | JSON 格式的 cookie 字符串 |
| proxyMethod | number | 是 | 代理方式：2 自定义 / 3 提取 IP |
| proxyType | string | 否 | 代理类型：noproxy / http / https / socks5 / ssh |
| host | string | 否 | 代理主机 |
| port | number | 否 | 代理端口 |
| proxyUserName | string | 否 | 代理账号 |
| proxyPassword | string | 否 | 代理账号密码 |
| ipCheckService | string | 否 | IP 查询库：ip-api / ip123in / luminati |
| isIpv6 | string | 否 | 是否 IPv6，默认 false |
| refreshProxyUrl | string | 否 | 代理刷新 URL |
| enableSocks5Udp | boolean | 否 | 是否开启 UDP 协议（socks5） |
| country / province / city | string | 否 | 国家/省/市 code（动态代理用） |
| workbench | string | 否 | 工作台：localserver / disable |
| abortImage | boolean | 否 | 禁止加载图片，默认 false |
| abortImageMaxSize | number | 否 | 禁止加载超过指定大小(KB)的图片 |
| abortMedia | boolean | 否 | 禁止视频自动播放，默认 false |
| muteAudio | boolean | 否 | 浏览器静音，默认 false |
| stopWhileNetError | boolean | 否 | 网络不通停止打开，默认 false |
| stopWhileIpChange | boolean | 否 | IP 变化停止打开，默认 false |
| stopWhileCountryChange | boolean | 否 | IP 国家变化停止打开，默认 false |
| dynamicIpUrl | string | 否 | proxyMethod=3 时，提取 IP 链接 |
| dynamicIpChannel | string | 否 | 提取链接服务商：rola / doveip / cloudam / common |
| isDynamicIpChangeIp | boolean | 否 | 每次打开都提取新 IP，默认 false |
| duplicateCheck | number | 否 | 提取 IP 校验重复：1 校验 / 0 不校验 |
| isGlobalProxyInfo | boolean | 否 | 使用全局动态代理信息 |
| syncTabs | boolean | 否 | 同步浏览器 tabs，默认 true |
| syncCookies | boolean | 否 | 同步 Cookie，默认 true |
| syncIndexedDb | boolean | 否 | 同步 IndexedDB，默认 false |
| syncLocalStorage | boolean | 否 | 同步 Local Storage，默认 false |
| syncBookmarks | boolean | 否 | 同步书签，默认 false |
| syncAuthorization | boolean | 否 | 同步已保存密码，默认 false |
| syncHistory | boolean | 否 | 同步历史记录，默认 false |
| syncExtensions | boolean | 否 | 同步扩展数据，默认 false |
| credentialsEnableService | boolean | 否 | 禁止保存密码弹窗，默认 false |
| isValidUsername | boolean | 否 | 根据平台/用户名/密码校验重复（创建时有效） |
| allowedSignin | boolean | 否 | 允许 Google 账号登录浏览器，默认 false |
| clearCacheFilesBeforeLaunch | boolean | 否 | 启动前清理缓存文件 |
| clearCacheWithoutExtensions | boolean | 否 | 启动前清理缓存（保留扩展数据） |
| clearCookiesBeforeLaunch | boolean | 否 | 启动前清理 Cookie |
| clearHistoriesBeforeLaunch | boolean | 否 | 启动前清理历史记录 |
| randomFingerprint | boolean | 否 | 每次启动均随机指纹 |
| disableGpu | boolean | 否 | 关闭 GPU 硬件加速，默认 false |
| disableTranslatePopup | boolean | 否 | 禁止谷歌翻译弹窗，默认 false |
| disableNotifications | boolean | 否 | 禁止消息通知弹窗，默认 false |
| disableClipboard | boolean | 否 | 禁止网站读取剪贴板，默认 false |
| memorySaver | boolean | 否 | 省内存模式（不建议开启），默认 false |
| browserFingerPrint | object | 是 | 指纹对象（见下方） |

#### browserFingerPrint 指纹对象

| 名称 | 类型 | 说明 |
|------|------|------|
| coreProduct | string | 内核：chrome / firefox，默认 chrome |
| coreVersion | string | 内核版本，chrome 默认 130，firefox 默认 128 |
| ostype | string | 操作系统平台：PC / Android / IOS |
| os | string | navigator.platform 值：Win32 / MacIntel / Linux x86_64 / iPhone / Linux armv81 |
| osVersion | string | 操作系统版本，不填则按 os 随机 |
| version | string | 浏览器版本，不填则随机，建议与 coreVersion 一致 |
| userAgent | string | UA，不填则自动生成 |
| isIpCreateTimeZone | boolean | 基于 IP 生成时区，默认 true |
| timeZone | string | 时区（isIpCreateTimeZone=false 时设置） |
| timeZoneOffset | number | 时区偏移量 |
| webRTC | string | WebRTC 策略：0 替换 / 1 允许 / 2 禁止 / 3 隐私 |
| ignoreHttpsErrors | boolean | 忽略 HTTPS 证书错误 |
| position | string | 地理位置：0 询问 / 1 允许 / 2 禁止 |
| isIpCreatePosition | boolean | 基于 IP 生成地理位置，默认 true |
| lat / lng | string | 纬度/经度（手动设置时） |
| isIpCreateLanguage | boolean | 基于 IP 生成浏览器语言，默认 true |
| languages | string | 浏览器语言（手动设置时） |
| isIpCreateDisplayLanguage | boolean | 基于 IP 生成界面语言 |
| openWidth / openHeight | number | 窗口打开时尺寸（与指纹无关） |
| resolutionType | string | 分辨率类型：0 跟随电脑 / 1 自定义 |
| resolution | string | 自定义分辨率值，如 "1920 x 1080" |
| windowSizeLimit | boolean | 约束窗口最大尺寸不超过分辨率 |
| devicePixelRatio | number | 显示缩放比例，建议 1 / 1.5 / 2 / 2.5 / 3 |
| fontType | string | 字体生成类型：0 系统默认 / 2 随机 |
| canvas | string | Canvas：0 随机 / 1 关闭 |
| webGL | string | WebGL 图像：0 随机 / 1 关闭 |
| webGLMeta | string | WebGL 元数据：0 自定义 / 1 关闭 |
| audioContext | string | AudioContext：0 随机 / 1 关闭 |
| mediaDevice | string | 媒体设备：0 随机 / 1 关闭 |
| speechVoices | string | Speech Voices：0 随机 / 1 关闭 |
| hardwareConcurrency | string | 硬件并发数 |
| deviceMemory | string | 设备内存（4 或 8，勿大于 8） |
| doNotTrack | string | Do Not Track：1 开启 / 0 关闭 |
| clientRectNoiseEnabled | boolean | 使用匹配值替代真实 ClientRects，默认 true |
| portScanProtect | string | 端口扫描保护：0 开启 / 1 关闭 |
| portWhiteList | string | 端口白名单，逗号分隔 |
| deviceInfoEnabled | boolean | 自定义设备信息，默认 true |
| computerName / macAddr / hostIP | string | 设备信息（建议留空自动生成） |
| disableSslCipherSuitesFlag | boolean | SSL 禁用特性，默认 false |
| enablePlugins | boolean | 是否启用插件指纹，默认 false |
| launchArgs | string | 启动参数，如 "--incognito"，多个用逗号分隔 |

---

### 3. 修改窗口属性（支持批量）

**POST** `/browser/update/partial`

只传需要更新的字段即可，支持批量修改（传入 ids 数组）。修改代理需使用专用接口 `/browser/proxy/update`。

```json
{
  "ids": ["id1", "id2"],
  "name": "修改的name",
  "groupId": "xxx"
}
```

---

### 4. 打开浏览器窗口

**POST** `/browser/open`

返回 `ws`（WebSocket 地址，用于 Playwright）、`http`（调试地址，用于 Selenium）、`coreVersion`、`driver`（chromedriver 路径）。

| 名称 | 类型 | 必选 | 说明 |
|------|------|------|------|
| id | string | 是 | 浏览器窗口 ID |
| args | array | 否 | chromium 启动参数数组 |
| queue | boolean | 否 | 队列方式打开，防止并发报错 |
| ignoreDefaultUrls | boolean | 否 | 忽略已同步的 URL |
| newPageUrl | string | 否 | 指定打开的 URL（需配合 ignoreDefaultUrls） |

**常用 args 参数：**
- `--remote-debugging-address=0.0.0.0` — 放通局域网端口
- `--headless` — 无头模式
- `--incognito` — 隐身模式
- `--load-extension=路径` — 加载扩展

**返回数据示例：**
```json
{
  "success": true,
  "data": {
    "ws": "ws://127.0.0.1:53325/devtools/browser/xxx",
    "http": "127.0.0.1:53325",
    "coreVersion": "112",
    "driver": "/path/to/chromedriver/112/chromedriver",
    "pid": 31295
  }
}
```

---

### 5. 关闭浏览器窗口

**POST** `/browser/close`

调用后需等待 **5 秒**再进行删除或重新打开操作。

```json
{ "id": "xxx" }
```

---

### 6. 重置浏览器关闭状态

**POST** `/browser/closing/reset`

仅用于窗口异常关闭后状态卡住的情况。使用前需确认窗口已实际关闭。

```json
{ "id": "xxx" }
```

---

### 7. 删除浏览器窗口

**POST** `/browser/delete`

彻底删除，无法从回收站找回。

```json
{ "id": "xxx" }
```

---

### 8. 获取浏览器窗口详情

**POST** `/browser/detail`

返回窗口完整配置信息，包括代理、指纹、同步设置等所有字段。

```json
{ "id": "xxx" }
```

---

## 接口请求参数示例

> 来源：https://doc2.bitbrowser.cn/jiekou/request.html

以下为各场景的请求参数示例，仅展示部分字段，完整字段参考对应接口文档。

### 创建 Windows 窗口

```json
// 接口：/browser/update
{
  "name": "windows browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "PC",
    "os": "Win32",
    "osVersion": "11,10"
  },
  "proxyMethod": 2,
  "proxyType": "noproxy"
}
```

### 创建 Mac 窗口

```json
// 接口：/browser/update
{
  "name": "mac browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "PC",
    "os": "MacIntel",
    "hardwareConcurrency": "10"
  },
  "proxyMethod": 2,
  "proxyType": "noproxy"
}
```

### 创建 Linux 窗口

```json
// 接口：/browser/update
{
  "name": "Linux browser",
  "browserFingerPrint": {
    "coreVersion": "124",
    "ostype": "PC",
    "os": "Linux x86_64"
  },
  "proxyMethod": 2,
  "proxyType": "noproxy"
}
```

### 创建 iPhone 窗口

```json
// 接口：/browser/update
{
  "name": "iphone browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "IOS",
    "os": "iPhone",
    "openWidth": 500,
    "openHeight": 900,
    "resolutionType": "1",
    "resolution": "360x780",
    "devicePixelRatio": 3
  },
  "proxyMethod": 2,
  "proxyType": "noproxy"
}
```

### 创建 Android 窗口

```json
// 接口：/browser/update
{
  "name": "android browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "Android",
    "os": "Linux armv81",
    "openWidth": 500,
    "openHeight": 900,
    "resolutionType": "1",
    "resolution": "360x780",
    "devicePixelRatio": 2
  },
  "proxyMethod": 2,
  "proxyType": "noproxy"
}
```

### 修改窗口信息（不改指纹）

```json
// 接口：/browser/update/partial
{
  "ids": ["d2fc7636d01b4943a3c3bd2187ca2272"],
  "name": "我是修改的",
  "browserFingerPrint": {}  // 不修改指纹，则无需传入指纹配置
}
```

### 修改窗口指纹信息

修改设备类型时（如 PC 改为 Android），需将相关字段一并修改：

```json
// 接口：/browser/update/partial
{
  "ids": ["d1982fc6322545d4a372275238b65c2f"],
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "Android",
    "os": "Linux armv81",
    "version": "",
    "osVersion": "",
    "platformVersion": "9.0.0",
    "batchRandom": true,
    "batchUpdateFingerPrint": true
  }
}
```

### 创建窗口并设置 socks5 代理

```json
{
  "name": "windows browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "PC",
    "os": "Win32",
    "osVersion": "11,10"
  },
  "proxyMethod": 2,
  "proxyType": "socks5",
  "host": "1.2.3.4",
  "port": 1020,
  "proxyUserName": "abc",
  "proxyPassword": "def"
}
```

### 创建窗口并设置代理为 API 提取链接

```json
{
  "name": "windows browser",
  "browserFingerPrint": {
    "coreVersion": "118",
    "ostype": "PC",
    "os": "Win32",
    "osVersion": "11,10"
  },
  "ipCheckService": "ip123in",
  "proxyMethod": 3,
  "proxyType": "socks5",
  "dynamicIpUrl": "http://example.tiquip.com/tiqu",
  "dynamicIpChannel": "common",
  "isDynamicIpChangeIp": true
}
```

---

## 模块说明

### bit_selenium.py

使用 Selenium 连接 BitBrowser 打开的浏览器实例，通过 `debuggerAddress` 和 `driver` 路径实现绑定。示例流程：打开百度 → 输入关键词 → 点击搜索。

### bit_playwright.py

使用 Playwright（异步模式）通过 CDP（Chrome DevTools Protocol）连接 BitBrowser 打开的浏览器实例。示例流程：打开百度页面 → 延时关闭。

## 依赖

- Python 3
- `requests` — HTTP 请求
- `selenium` — Selenium 自动化（bit_selenium.py）
- `playwright` — Playwright 自动化（bit_playwright.py）

## 运行前提

1. 安装并启动 BitBrowser 客户端
2. 确保本地服务运行在 `http://127.0.0.1:54345`
3. 安装所需依赖：`pip install requests selenium playwright`

## 使用流程

1. 调用 `bit_api.py` 中的 API 创建/打开浏览器窗口
2. 获取返回的连接地址（`ws` 用于 Playwright，`http` + `driver` 用于 Selenium）
3. 使用 Selenium 或 Playwright 连接并执行自动化操作
4. 操作完成后调用 `closeBrowser()` 关闭窗口

---

## 无头模式指南

> 来源：https://doc2.bitbrowser.cn/headless.html

### 使用方式

**方式一：通过 /browser/open 的 args 参数传入**

```json
// 接口：/browser/open
{
    "id": "3baa6e990fee4e839c72722c8dc18019",
    "args": ["--headless"],
    "queue": true,
    "ignoreDefaultUrls": true  // 一定要加这个参数，不要配置 newPageUrl，窗口打开后通过脚本自行打开 page
}
```

**方式二：创建/修改窗口时在指纹对象中设置 launchArgs**

```json
// 创建或修改窗口接口（/browser/update 或 /browser/update/partial）
{
    "url": "",  // 一定要设置 url 为空
    "browserFingerPrint": {
        "launchArgs": "--headless"  // 启动参数，可逗号分隔传入多个
    }
}
```

### 常见问题

当出现以下报错时：

```json
{
    "success": false,
    "msg": "打开窗口失败... Multiple targets are not supported in headless mode."
}
```

**原因：** 无头模式不支持启动时打开多个 URL。需确保 `ignoreDefaultUrls: true` 且不配置 `newPageUrl`，窗口打开后通过脚本自行导航页面。
