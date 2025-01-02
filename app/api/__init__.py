from flask import Blueprint, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename
from app.config import Config
import json
from pydub import AudioSegment
import io
import tempfile
from pydub.utils import which
import time

bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'mp4'}

if not which("ffmpeg"):
    # 获取项目根目录下的 bin 文件夹路径
    bin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bin')
    # 设置 ffmpeg 路径
    os.environ["PATH"] += os.pathsep + bin_path

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def call_huggingface_api(audio_content, headers, max_retries=5, initial_wait=20):
    API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v2"
    
    for attempt in range(max_retries):
        response = requests.post(API_URL, headers=headers, data=audio_content)
        
        if response.status_code == 200:
            return response.json()
        
        # 如果是模型加载错误
        if response.status_code == 503:
            try:
                error_data = response.json()
                if "estimated_time" in error_data:
                    # 使用估计时间，但不少于 initial_wait 秒
                    wait_time = max(initial_wait, int(error_data["estimated_time"]) + 5)
                else:
                    wait_time = initial_wait * (attempt + 1)  # 递增等待时间
                
                print(f"模型正在加载，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            except json.JSONDecodeError:
                wait_time = initial_wait * (attempt + 1)
                time.sleep(wait_time)
                continue
        
        # 其他错误直接抛出
        raise Exception(f'API错误: {response.status_code} - {response.text}')
    
    raise Exception('达到最大重试次数，模型仍未加载完成')

@bp.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # 保存上传的文件到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                file.save(temp_file.name)
                
            # 使用 pydub 加载音频
            audio = AudioSegment.from_file(temp_file.name)
            
            # 分割音频为30秒的片段
            segment_length = 30 * 1000  # 30 seconds in milliseconds
            segments = []
            
            for i in range(0, len(audio), segment_length):
                segment = audio[i:i + segment_length]
                segments.append(segment)
            
            # 处理每个片段
            full_text = []
            headers = {
                "Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}",
                "Content-Type": "audio/wav"
            }
            
            for i, segment in enumerate(segments):
                # 将片段导出为临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as segment_file:
                    segment.export(segment_file.name, format='wav')
                    
                    # 调用 Hugging Face API
                    with open(segment_file.name, 'rb') as f:
                        audio_content = f.read()
                        result = call_huggingface_api(audio_content, headers)
                        
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get('text', '')
                        elif isinstance(result, dict):
                            text = result.get('text', '')
                        else:
                            text = str(result)
                        
                        full_text.append(text)
                
                # 清理临时文件
                os.unlink(segment_file.name)
            
            # 清理原始临时文件
            os.unlink(temp_file.name)
            
            # 合并所有文本
            final_text = ' '.join(full_text)
            
            return jsonify({
                'success': True,
                'text': final_text
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'处理请求时出错: {str(e)}'
            }), 500
    
    return jsonify({'success': False, 'error': '不支持的文件格式'}), 400