# routes/config_management.py
from flask import Blueprint, render_template, request, jsonify, flash
from functools import wraps
from auth import requires_auth

config_bp = Blueprint('config', __name__)

def validate_config_access(f):
    """Decorator to validate configuration access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.authorization.username != 'admin':
            return jsonify({
                'success': False,
                'message': 'Only admin users can modify configuration'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

@config_bp.route('/settings', methods=['GET'])
@requires_auth
def settings():
    """Display configuration settings page"""
    config = current_app.config_manager.get_config()
    backups = current_app.config_manager.list_backups()
    
    # Group settings by category
    settings_groups = {
        'GPIO Configuration': {k: v for k, v in asdict(config).items() if k.endswith('_PIN')},
        'Timing Configuration': {k: v for k, v in asdict(config).items() if k.endswith('_INTERVAL')},
        'Security Configuration': {
            'LOGIN_ATTEMPTS_MAX': config.LOGIN_ATTEMPTS_MAX,
            'LOGIN_ATTEMPTS_WINDOW': config.LOGIN_ATTEMPTS_WINDOW,
            'SESSION_TIMEOUT': config.SESSION_TIMEOUT
        },
        'Storage Configuration': {k: v for k, v in asdict(config).items() if k.endswith('_DIR')},
        'Image Configuration': {
            'IMAGE_RESOLUTION': config.IMAGE_RESOLUTION,
            'IMAGE_QUALITY': config.IMAGE_QUALITY,
            'MOTION_DETECTION_SENSITIVITY': config.MOTION_DETECTION_SENSITIVITY
        },
        'Notification Configuration': {k: v for k, v in asdict(config).items() 
                                     if k.startswith('SMTP_') or k.endswith('_EMAIL')}
    }
    
    return render_template(
        'settings.html',
        settings_groups=settings_groups,
        backups=backups
    )

@config_bp.route('/api/settings', methods=['POST'])
@requires_auth
@validate_config_access
def update_settings():
    """Update configuration settings"""
    try:
        updates = request.get_json()
        success, message = current_app.config_manager.update_config(updates)
        
        if success:
            # Reload necessary components
            if any(k.endswith('_PIN') for k in updates.keys()):
                current_app.security_monitor.setup_gpio()
            if 'IMAGE_RESOLUTION' in updates:
                current_app.security_monitor.setup_camera()
                
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error updating settings: {str(e)}"
        }), 500

@config_bp.route('/api/settings/backup', methods=['POST'])
@requires_auth
@validate_config_access
def restore_backup():
    """Restore configuration from backup"""
    try:
        backup_file = request.json.get('backup_file')
        if not backup_file:
            return jsonify({
                'success': False,
                'message': 'No backup file specified'
            }), 400
            
        success, message = current_app.config_manager.restore_backup(backup_file)
        if success:
            # Reload all components
            current_app.security_monitor.setup_gpio()
            current_app.security_monitor.setup_camera()
            current_app.security_monitor.setup_lcd()
            
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error restoring backup: {str(e)}"
        }), 500