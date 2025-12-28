# [计划] 添加 "Powered by 数智技术中心" 页脚

本计划旨在将 "Powered by 数智技术中心" 作为一个标准页脚添加到系统的主要界面中。

## 1. 目标页面与位置
我们需要修改以下文件以覆盖所有目标页面：

1.  **测评人员登录页**: `templates/login_assessment.html` (最下方)
2.  **管理员登录页**: `templates/login_admin.html` (最下方)
3.  **管理员后台布局基类**: `templates/base.html` (右侧内容区域最下方)
4.  **测评后台布局基类**: `templates/base_assessment.html` (右侧内容区域最下方)

## 2. 样式与内容
- **文字内容**: Powered by 数智技术中心
- **样式**:
    - 颜色: 灰色/静默色 (text-muted)
    - 大小: 小字体 (small / font-size: 0.8rem)
    - 对齐: 居中 (text-center)
    - 边距: 顶部适量间距 (mt-3 / py-3)

## 3. 实施步骤

### 3.1 修改登录页面
针对 `login_assessment.html` 和 `login_admin.html`，在主要的容器 `container-tight` 结束前，或者 `page` 容器结束前添加页脚。

**代码片段**:
```html
<div class="text-center text-muted mt-3 pb-3" style="font-size: 0.8rem;">
    Powered by 数智技术中心
</div>
```
*(注：登录页已有 "管理员入口" 链接，可以将页脚放在其下方)*

### 3.2 修改布局基类 (Base Templates)
针对 `base.html` 和 `base_assessment.html`，在 `.page-wrapper` 内部，`.page-body` 之后，添加标准的 Tabler 页脚结构。

**代码片段**:
```html
<footer class="footer footer-transparent d-print-none">
    <div class="container-xl">
        <div class="row text-center align-items-center flex-row-reverse">
            <div class="col-12 col-lg-auto mt-3 mt-lg-0">
                <ul class="list-inline list-inline-dots mb-0">
                    <li class="list-inline-item">
                        Powered by 数智技术中心
                    </li>
                </ul>
            </div>
        </div>
    </div>
</footer>
```
或者更简单的版本（如果不需要复杂的 Tabler Footer 结构）：
```html
<div class="text-center text-muted py-3">
    Powered by 数智技术中心
</div>
```
(考虑到用户要求“网页上常规写法”，我们将使用简单的居中灰字)

## 4. 验证计划
1.  启动服务器。
2.  分别访问评估登录页、管理员登录页、评估首页、管理员后台首页。
3.  确认所有页面底部均显示 "Powered by 数智技术中心"。
