// Clash Config Manager - 前端脚本

/**
 * 更新配置
 */
function updateConfig() {
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'status info';
    resultDiv.innerHTML = '<p>⏳ 正在更新配置...</p>';
    
    fetch('/update-config', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            resultDiv.className = 'status ' + (data.status === 'success' ? 'success' : 'error');
            resultDiv.innerHTML = '<h3>更新结果</h3><p>' + data.message + '</p><p>时间: ' + data.timestamp + '</p>';
        })
        .catch(error => {
            resultDiv.className = 'status error';
            resultDiv.innerHTML = '<h3>❌ 更新失败</h3><p>' + error + '</p>';
        });
}

/**
 * 检查服务状态
 */
function checkStatus() {
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'status info';
    resultDiv.innerHTML = '<p>⏳ 正在检查状态...</p>';
    
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            resultDiv.className = 'status info';
            resultDiv.innerHTML = '<h3>📊 状态信息</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
        })
        .catch(error => {
            resultDiv.className = 'status error';
            resultDiv.innerHTML = '<h3>❌ 检查失败</h3><p>' + error + '</p>';
        });
}

