// 设备控制函数
function setDeviceStatus(device, status) {
    fetch(`/api/device/${device}/${status}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 更新按钮状态
                const btn = document.querySelector(`.device-btn[data-device="${device}"]`);
                if (btn) {
                    const newStatus = status === 'ON' ? 'OFF' : 'ON';
                    btn.textContent = `设置为${newStatus}`;
                    btn.setAttribute('onclick', `setDeviceStatus('${device}', '${newStatus}')`);

                    // 更新状态显示
                    const statusEl = document.querySelector(`.device-status[data-device="${device}"]`);
                    if (statusEl) {
                        statusEl.textContent = status;
                        statusEl.className = `device-status status-${status.toLowerCase()}`;
                    }
                }
            } else {
                alert('操作失败: ' + (data.message || '未知错误'));
            }
        })
        .catch(error => console.error('操作失败:', error));
}

// 切换控制模式
function toggleControlMode() {
    if (confirm('确定要切换控制模式吗？')) {
        fetch('/api/mode/toggle', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const modeText = data.auto_mode ? '自动' : '手动';
                    document.getElementById('current-mode').textContent = `当前模式: ${modeText}`;

                    // 启用/禁用设备控制按钮
                    const buttons = document.querySelectorAll('.device-btn');
                    buttons.forEach(btn => {
                        btn.disabled = data.auto_mode && document.getElementById('user-role').value !== 'admin';
                    });
                }
            });
    }
}

// 处理报警
function handleAlert(alertId) {
    if (confirm('确定要标记此报警为已处理吗？')) {
        fetch(`/api/alert/${alertId}/handle`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const alertEl = document.getElementById(`alert-${alertId}`);
                    if (alertEl) {
                        alertEl.classList.add('alert-handled');
                        const handleBtn = alertEl.querySelector('.handle-btn');
                        if (handleBtn) {
                            handleBtn.remove();
                        }
                        alertEl.innerHTML += '<p><strong>状态:</strong> 已处理</p>';
                    }
                } else {
                    alert('处理失败');
                }
            });
    }
}

// 更新阈值
function updateThreshold(param) {
    const value = prompt(`请输入新的${param}阈值:`);
    if (value !== null && !isNaN(value)) {
        fetch(`/api/threshold/${param}/${parseFloat(value)}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('阈值更新成功');
                    location.reload();
                } else {
                    alert('更新失败');
                }
            });
    }
}

// 实时更新时间
function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').textContent =
        now.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
}
setInterval(updateTime, 1000);  // 每秒更新一次
updateTime();  // 页面加载时立即执行一次