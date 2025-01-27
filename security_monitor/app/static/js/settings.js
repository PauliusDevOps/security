document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    
    settingsForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {};
        const inputs = settingsForm.querySelectorAll('input');
        
        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                formData[input.name] = input.checked;
            } else if (input.type === 'number') {
                formData[input.name] = parseInt(input.value);
            } else {
                formData[input.name] = input.value;
            }
        });
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            showAlert(result.success ? 'success' : 'danger', result.message);
            
            if (result.success) {
                setTimeout(() => window.location.reload(), 2000);
            }
        } catch (error) {
            showAlert('danger', 'Error saving settings: ' + error.message);
        }
    });
    
    function showAlert(type, message) {
        const alertContainer = document.getElementById('alert-container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        alertContainer.innerHTML = '';
        alertContainer.appendChild(alert);
        
        setTimeout(() => alert.remove(), 5000);
    }
});