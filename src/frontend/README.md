# Frontend 前端资源目录

此目录包含 Clash Config Manager Web 界面的所有前端资源。

## 📁 目录结构

```
frontend/
├── html/           # HTML 模板文件
│   └── index.html  # 主页模板
├── css/            # CSS 样式表
│   └── style.css   # 主样式表
└── js/             # JavaScript 脚本
    └── app.js      # 主应用脚本
```

## 🎨 资源说明

### HTML 模板 (`html/`)

- **`index.html`** - 主页模板
  - 使用 Jinja2 模板语法
  - 动态变量：`current_time`, `last_update`, `config_exists`
  - 响应式设计

### CSS 样式 (`css/`)

- **`style.css`** - 主样式表
  - 响应式布局
  - 状态卡片样式（success, info, error）
  - 按钮和交互元素样式
  - 代码块样式

### JavaScript 脚本 (`js/`)

- **`app.js`** - 前端交互脚本
  - `manualUpdate()` - 手动更新配置
  - `checkStatus()` - 检查服务状态
  - 使用 Fetch API 与后端交互

## 🔗 Flask 配置

在 `src/app.py` 中的配置：

```python
template_dir = Path(__file__).parent / "frontend" / "html"
static_dir = Path(__file__).parent / "frontend"

app = Flask(
    __name__,
    template_folder=str(template_dir),
    static_folder=str(static_dir),
    static_url_path="/static"
)
```

## 📄 静态文件引用

在 HTML 模板中引用静态文件：

```html
<!-- CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

<!-- JavaScript -->
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
```

## 🎯 API 接口

前端调用的后端接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页（渲染 index.html） |
| `/status` | GET | 获取服务状态（JSON） |
| `/manual-update` | POST | 手动触发配置更新 |

## 🛠️ 开发建议

### 修改样式

编辑 `css/style.css` 文件，无需重启容器（刷新浏览器即可）。

### 修改脚本

编辑 `js/app.js` 文件，清除浏览器缓存后刷新。

### 修改模板

编辑 `html/index.html` 文件，重启容器使更改生效：

```bash
docker compose restart
```

或在开发模式下，Flask 会自动重载：

```python
app.run(host=host, port=port, debug=True)  # 开启 debug 模式
```

## 📦 Docker 部署

前端资源在 Dockerfile 中通过以下命令复制到容器：

```dockerfile
COPY --chown=appuser:appuser src/ ./src/
```

这会自动包含整个 `src/frontend/` 目录。

## 🎨 自定义主题

如需自定义主题颜色，修改 `css/style.css` 中的以下变量：

```css
/* 主色调 */
button {
    background: #007bff;  /* 修改为你喜欢的颜色 */
}

/* 状态颜色 */
.success { border-left-color: #28a745; }  /* 成功：绿色 */
.info { border-left-color: #17a2b8; }     /* 信息：蓝色 */
.error { border-left-color: #dc3545; }    /* 错误：红色 */
```

## 📱 响应式设计

当前样式支持桌面和移动设备，容器最大宽度为 800px。

如需调整：

```css
.container {
    max-width: 800px;  /* 修改为所需宽度 */
}
```

---

**前端技术栈**：
- HTML5
- CSS3
- Vanilla JavaScript (无框架)
- Flask Jinja2 模板引擎

