"""HTTP/REST API routes for OAuth and health checks"""
import os
import requests
from flask import Blueprint, request, jsonify
from config.settings import CLIENT_ID

# Get credentials from environment
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend service running'})


@api_bp.route('/exchange-code', methods=['POST']) 
def exchange_code():
    """Exchange Google authorization code for access + refresh tokens"""
    data = request.json
    code = data.get('code')
    redirect_uri = data.get('redirect_uri')
    
    if not code or not redirect_uri:
        return jsonify({'error': 'Missing code or redirect_uri'}), 400
    
    try:
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token exchange failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        return jsonify({
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/refresh-token', methods=['POST'])  
def refresh_token():
    """Get new access token using refresh token"""
    data = request.json
    refresh_token_value = data.get('refresh_token')
    
    if not refresh_token_value:
        return jsonify({'error': 'Missing refresh_token'}), 400
    
    try:
        response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'refresh_token': refresh_token_value,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'refresh_token'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token refresh failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        return jsonify({
            'access_token': token_data.get('access_token'),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/github/exchange-code', methods=['POST'])
def github_exchange_code():
    """Exchange GitHub authorization code for access token"""
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'Missing code'}), 400
    
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return jsonify({'error': 'GitHub OAuth not configured'}), 500
    
    try:
        response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            data={
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Token exchange failed',
                'details': response.text
            }), response.status_code
        
        token_data = response.json()
        
        if 'error' in token_data:
            return jsonify({
                'error': token_data.get('error_description', 'Token exchange failed')
            }), 400
        
        return jsonify({
            'access_token': token_data.get('access_token'),
            'token_type': token_data.get('token_type', 'bearer'),
            'scope': token_data.get('scope', '')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
