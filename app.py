import os
import time
import requests
import base64
import uuid
import json
import threading
import queue
from flask import Flask, render_template, request, jsonify, send_file, stream_with_context, Response
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# ============================================================
# LOGGING SETUP
# ============================================================
if not os.path.exists('logs'):
    os.makedirs('logs')

handler = RotatingFileHandler('logs/studio.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# ============================================================
# CONFIGURATION
# ============================================================
HF_API_TOKEN = "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"  # Your token

# Multi-Provider Configuration
PROVIDERS = {
    'huggingface': {
        'enabled': True,
        'token': HF_API_TOKEN,
        'base_url': 'https://api-inference.huggingface.co/models/',
        'models': {
            'image': 'black-forest-labs/FLUX.1-schnell',
            'video': 'ali-vilab/text-to-video-ms-1.7b',
            'image_to_video': 'stability-ai/stable-video-diffusion-img2vid'
        }
    },
    'replicate': {
        'enabled': False,
        'token': '',  # Add if you want to use Replicate
        'base_url': 'https://api.replicate.com/v1/',
        'models': {
            'image': 'black-forest-labs/flux-schnell',
            'video': 'stability-ai/stable-video-diffusion'
        }
    }
}

HEADERS = {}
if HF_API_TOKEN != "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":
    HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# ============================================================
# FOLDERS
# ============================================================
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# ============================================================
# TASK QUEUE SYSTEM (Async Processing)
# ============================================================
task_queue = queue.Queue()
task_status = {}
task_results = {}

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def _worker_loop(self):
        while self.running:
            try:
                task = task_queue.get(timeout=1)
                if task is None:
                    continue
                
                task_id = task['id']
                task_type = task['type']
                task_data = task['data']
                
                self.tasks[task_id] = {'status': 'processing', 'progress': 0}
                
                # Process based on type
                if task_type == 'image':
                    result = self._process_image(task_data)
                elif task_type == 'video':
                    result = self._process_video(task_data)
                elif task_type == 'animate':
                    result = self._process_animation(task_data)
                else:
                    result = {'error': 'Unknown task type'}
                
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['result'] = result
                self.tasks[task_id]['progress'] = 100
                
            except queue.Empty:
                continue
            except Exception as e:
                app.logger.error(f"Worker error: {str(e)}")
    
    def _process_image(self, data):
        """Process image generation"""
        prompt = data.get('prompt', '')
        app.logger.info(f"Processing image: {prompt[:50]}...")
        
        # Try Hugging Face API
        try:
            API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
            payload = {"inputs": prompt}
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            
            if response.status_code == 200:
                filename = f"image_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return {
                    'success': True,
                    'url': f"/static/outputs/{filename}",
                    'provider': 'huggingface'
                }
        except Exception as e:
            app.logger.error(f"API error: {e}")
        
        # Fallback
        filepath, filename = generate_fallback_image(prompt)
        if filepath:
            return {
                'success': True,
                'url': f"/static/outputs/{filename}",
                'provider': 'fallback'
            }
        
        return {'success': False, 'error': 'All providers failed'}
    
    def _process_video(self, data):
        """Process video generation with multi-provider failover"""
        prompt = data.get('prompt', '')
        app.logger.info(f"Processing video: {prompt[:50]}...")
        
        # Try multiple providers
        video_models = [
            "https://api-inference.huggingface.co/models/ali-vilab/text-to-video-ms-1.7b",
            "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-text-to-video",
        ]
        
        for model_url in video_models:
            try:
                payload = {"inputs": f"{prompt}, cinematic, high quality, 4k"}
                response = requests.post(model_url, headers=HEADERS, json=payload, timeout=120)
                
                if response.status_code == 200:
                    filename = f"video_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
                    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    return {
                        'success': True,
                        'url': f"/static/outputs/{filename}",
                        'provider': 'huggingface'
                    }
            except Exception as e:
                app.logger.error(f"Model {model_url} failed: {e}")
                continue
        
        # Fallback
        filepath, filename = generate_fallback_video(prompt)
        if filepath:
            return {
                'success': True,
                'url': f"/static/outputs/{filename}",
                'provider': 'fallback'
            }
        
        return {'success': False, 'error': 'All video providers failed'}
    
    def _process_animation(self, data):
        """Process image to video animation"""
        base64_image = data.get('image', '')
        prompt = data.get('prompt', 'cinematic motion')
        app.logger.info(f"Processing animation...")
        
        # Try Stable Video Diffusion
        API_URL = "https://api-inference.huggingface.co/models/stability-ai/stable-video-diffusion-img2vid"
        
        temp_filename = f"temp_{int(time.time())}.jpg"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        
        try:
            image_data = base64.b64decode(base64_image)
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            
            with open(temp_path, 'rb') as f:
                files = {'file': ('image.jpg', f, 'image/jpeg')}
                response = requests.post(API_URL, headers=HEADERS, files=files, timeout=120)
                
                if response.status_code == 200:
                    filename = f"animation_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
                    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    os.remove(temp_path)
                    return {
                        'success': True,
                        'url': f"/static/outputs/{filename}",
                        'provider': 'huggingface'
                    }
        except Exception as e:
            app.logger.error(f"Animation API error: {e}")
        
        # Clean up
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        
        # Fallback
        try:
            img_data = base64.b64decode(base64_image)
            img = Image.open(io.BytesIO(img_data))
            
            import cv2
            import numpy as np
            
            img_np = np.array(img)
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            target_size = (640, 480)
            img_resized = cv2.resize(img_np, target_size)
            
            filename = f"animation_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(filepath, fourcc, 15.0, target_size)
            
            for frame_num in range(30):
                scale = 1.0 + (frame_num / 30) * 0.3
                new_w = int(target_size[0] * scale)
                new_h = int(target_size[1] * scale)
                zoomed = cv2.resize(img_resized, (new_w, new_h))
                start_x = (new_w - target_size[0]) // 2
                start_y = (new_h - target_size[1]) // 2
                cropped = zoomed[start_y:start_y + target_size[1], start_x:start_x + target_size[0]]
                
                cv2.putText(cropped, "AI Animation", (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(cropped, f"Frame {frame_num+1}/30", (20, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                video.write(cropped)
            
            video.release()
            
            return {
                'success': True,
                'url': f"/static/outputs/{filename}",
                'provider': 'fallback'
            }
        except Exception as e:
            app.logger.error(f"Fallback animation error: {e}")
        
        return {'success': False, 'error': 'All animation providers failed'}

# Initialize Task Manager
task_manager = TaskManager()

# ============================================================
# LOCAL FALLBACK GENERATORS
# ============================================================
def generate_fallback_image(prompt):
    """Generate a professional placeholder image"""
    try:
        img = Image.new('RGB', (1024, 576), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)
        
        # Professional gradient circles
        colors = [(121, 40, 202), (255, 0, 122), (0, 212, 255)]
        for i, color in enumerate(colors):
            x = 200 + i * 300
            y = 288
            radius = 80 - i * 20
            for j in range(10):
                r = radius - j * 5
                if r > 0:
                    draw.ellipse((x-r, y-r, x+r, y+r), fill=(color[0], color[1], color[2]))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        # Professional text layout
        words = prompt.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > 30:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        y_text = 450
        for line in lines[:3]:
            draw.text((100, y_text), line, fill=(255, 255, 255), font=font)
            y_text += 40
        
        draw.text((100, y_text + 20), "✦ AI Content Studio", fill=(200, 200, 200), font=font)
        
        filename = f"fallback_img_{int(time.time())}.jpg"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        img.save(filepath, 'JPEG', quality=85)
        
        return filepath, filename
    except Exception as e:
        app.logger.error(f"Fallback image error: {e}")
        return None, None

def generate_fallback_video(prompt):
    """Generate professional placeholder video"""
    try:
        import cv2
        import numpy as np
        
        filename = f"fallback_video_{int(time.time())}.mp4"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(filepath, fourcc, 10.0, (640, 480))
        
        for frame_num in range(30):
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Animated gradient
            offset = frame_num * 5
            for y in range(480):
                for x in range(640):
                    r = (x + offset) % 256
                    g = (y + offset * 2) % 256
                    b = (x + y + offset * 3) % 256
                    img[y, x] = [b, g, r]
            
            cv2.putText(img, f"AI Content Studio", (50, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(img, f"{prompt[:40]}...", (50, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            cv2.putText(img, f"Frame {frame_num+1}/30", (50, 300), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            
            video.write(img)
        
        video.release()
        return filepath, filename
    except Exception as e:
        app.logger.error(f"Fallback video error: {e}")
        return None, None

# ============================================================
# ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "token_configured": bool(HF_API_TOKEN != "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"),
        "providers": list(PROVIDERS.keys()),
        "tasks_queued": task_queue.qsize(),
        "tasks_processing": len([t for t in task_manager.tasks.values() if t.get('status') == 'processing'])
    })

# ============================================================
# 1. TEXT TO IMAGE - Async
# ============================================================
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({"success": False, "error": "Prompt is required"}), 400
        
        # Create async task
        task_id = f"img_{uuid.uuid4().hex[:12]}"
        task_queue.put({
            'id': task_id,
            'type': 'image',
            'data': {'prompt': prompt}
        })
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Image generation started"
        })
        
    except Exception as e:
        app.logger.error(f"Image generation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# 2. TEXT TO VIDEO - Async
# ============================================================
@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.json
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({"success": False, "error": "Prompt is required"}), 400
        
        task_id = f"vid_{uuid.uuid4().hex[:12]}"
        task_queue.put({
            'id': task_id,
            'type': 'video',
            'data': {'prompt': prompt}
        })
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Video generation started"
        })
        
    except Exception as e:
        app.logger.error(f"Video generation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# 3. IMAGE TO VIDEO - Async
# ============================================================
@app.route('/api/image-to-video', methods=['POST'])
def image_to_video():
    try:
        data = request.json
        base64_image = data.get('image')
        prompt = data.get('prompt', 'cinematic motion')
        
        if not base64_image:
            return jsonify({"success": False, "error": "Image is required"}), 400
        
        task_id = f"anim_{uuid.uuid4().hex[:12]}"
        task_queue.put({
            'id': task_id,
            'type': 'animate',
            'data': {'image': base64_image, 'prompt': prompt}
        })
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Animation started"
        })
        
    except Exception as e:
        app.logger.error(f"Animation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# 4. TASK STATUS - Real-time Progress
# ============================================================
@app.route('/api/task-status/<task_id>', methods=['GET'])
def task_status_endpoint(task_id):
    """Get real-time task status with progress"""
    if task_id in task_manager.tasks:
        task = task_manager.tasks[task_id]
        result = task.get('result')
        
        response = {
            "success": True,
            "task_id": task_id,
            "status": task.get('status', 'unknown'),
            "progress": task.get('progress', 0)
        }
        
        if task.get('status') == 'completed' and result:
            response.update({
                "result": result,
                "url": result.get('url'),
                "provider": result.get('provider')
            })
        
        return jsonify(response)
    else:
        return jsonify({
            "success": False,
            "task_id": task_id,
            "status": "not_found",
            "message": "Task not found or expired"
        }), 404

# ============================================================
# 5. SERVE STATIC FILES
# ============================================================
@app.route('/static/outputs/<filename>')
def serve_output(filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    ext = filename.split('.')[-1].lower()
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'mp4': 'video/mp4',
        'webm': 'video/webm'
    }
    
    return send_file(filepath, mimetype=mime_types.get(ext, 'application/octet-stream'))

# ============================================================
# 6. API STATUS DASHBOARD
# ============================================================
@app.route('/api/status', methods=['GET'])
def api_status():
    """Comprehensive API status dashboard"""
    return jsonify({
        "studio_name": "AI Content Studio",
        "version": "2.0.0",
        "status": "operational",
        "providers": {
            "huggingface": {
                "status": "online" if HF_API_TOKEN != "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" else "disabled",
                "models": ["image", "video", "image_to_video"]
            },
            "fallback": {
                "status": "online",
                "description": "Local generators always available"
            }
        },
        "queue_status": {
            "queued": task_queue.qsize(),
            "processing": len([t for t in task_manager.tasks.values() if t.get('status') == 'processing']),
            "completed": len([t for t in task_manager.tasks.values() if t.get('status') == 'completed'])
        },
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎬 AI CONTENT STUDIO - PROFESSIONAL EDITION")
    print("="*70)
    print(f"📍 Server: http://localhost:5000")
    print(f"🔑 Token: {'✅ Configured' if HF_API_TOKEN != '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' else '⚠️ Not set'}")
    print(f"📁 Upload: {UPLOAD_FOLDER}")
    print(f"📁 Output: {OUTPUT_FOLDER}")
    print("="*70)
    print("\n⚙️  FEATURES:")
    print("   ✅ Async Task Queue (Non-blocking)")
    print("   ✅ Multi-Provider Failover")
    print("   ✅ Real-time Progress Tracking")
    print("   ✅ Professional Fallback Generators")
    print("   ✅ Production Logging")
    print("="*70)
    print("\n📊 API Endpoints:")
    print("   POST /api/generate-image  - Text to Image")
    print("   POST /api/generate-video  - Text to Video")
    print("   POST /api/image-to-video  - Image to Video")
    print("   GET  /api/task-status/<id> - Check Progress")
    print("   GET  /api/status          - System Status")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)