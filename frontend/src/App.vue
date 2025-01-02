<template>
  <div class="container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <h2>语音转文字</h2>
        </div>
      </template>

      <el-upload
        class="upload-demo"
        drag
        action=""
        :auto-upload="false"
        :show-file-list="true"
        :on-change="handleFileChange"
        accept=".mp3,.wav,.m4a,.mp4"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持的格式：MP3, WAV, M4A, MP4，文件大小不超过 100MB
          </div>
        </template>
      </el-upload>

      <el-button 
        type="primary" 
        @click="handleUpload" 
        :loading="loading"
        style="margin-top: 16px; width: 100%;"
      >
        开始转换
      </el-button>

      <el-progress 
        v-if="loading" 
        :percentage="totalProgress" 
        :format="format"
        class="progress-bar"
        :status="totalProgress === 100 ? 'success' : ''"
        :stroke-width="18"
      />

      <div v-if="result" class="result-section">
        <div class="result-header">
          <h3>转换结果</h3>
          <el-button 
            type="primary" 
            link 
            @click="copyResult"
            :icon="CopyDocument"
          >
            复制
          </el-button>
        </div>
        <el-input
          v-model="result"
          type="textarea"
          :rows="6"
          readonly
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'

const selectedFile = ref(null)
const loading = ref(false)
const progress = ref(0)
const result = ref('')
const processingProgress = ref(0)
const uploadProgress = ref(0)

// 计算总进度：上传进度占30%，处理进度占70%
const totalProgress = computed(() => {
  return Math.min(Math.round(uploadProgress.value * 0.3 + processingProgress.value * 0.7), 100)
})

// 模拟处理进度
let progressInterval
const startProcessingProgress = () => {
  processingProgress.value = 0
  clearInterval(progressInterval)
  
  progressInterval = setInterval(() => {
    if (processingProgress.value < 95) {
      // 逐渐减缓增长速度
      const increment = (95 - processingProgress.value) / 20
      processingProgress.value += Math.max(0.5, increment)
    }
  }, 1000)
}

const handleFileChange = (file) => {
  // 验证文件
  const isValidFile = validateFile(file.raw)
  if (!isValidFile) {
    return
  }
  selectedFile.value = file.raw
}

const validateFile = (file) => {
  const maxSize = 100 * 1024 * 1024  // 100MB
  const validExtensions = ['mp3', 'wav', 'm4a', 'mp4']
  
  // 获取文件扩展名
  const extension = file.name.split('.').pop().toLowerCase()
  
  // 检查文件扩展名
  if (!validExtensions.includes(extension)) {
    ElMessage.error('不支持的文件格式')
    return false
  }

  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }

  return true
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.error('请先选择文件')
    return
  }

  loading.value = true
  uploadProgress.value = 0
  processingProgress.value = 0
  result.value = ''

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    startProcessingProgress()

    const uploadResponse = await axios.post('/api/transcribe', formData, {
      timeout: 300000,  // 5分钟超时
      onUploadProgress: (progressEvent) => {
        uploadProgress.value = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
      }
    })

    if (uploadResponse.data.success) {
      clearInterval(progressInterval)
      processingProgress.value = 100
      uploadProgress.value = 100
      result.value = uploadResponse.data.text
      ElMessage.success('转换成功')
    } else {
      throw new Error(uploadResponse.data.error || '转换失败')
    }
  } catch (error) {
    clearInterval(progressInterval)
    if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error(error.message || '转换失败')
    }
    console.error('Error:', error)
  } finally {
    loading.value = false
  }
}

// 在组件卸载时清理定时器
onUnmounted(() => {
  clearInterval(progressInterval)
})

const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const format = (percentage) => {
  if (uploadProgress.value < 100) {
    return '上传中 ' + percentage + '%'
  } else if (percentage < 100) {
    return '处理中 ' + percentage + '%'
  } else {
    return '完成'
  }
}
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.upload-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-bar {
  margin: 20px 0;
}

.result-section {
  margin-top: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.upload-demo {
  margin-bottom: 16px;
}

:deep(.el-upload-dragger) {
  width: 100%;
}

:deep(.el-progress-bar__outer) {
  background-color: #e9ecef;
}

:deep(.el-progress-bar__inner) {
  transition: width 0.3s ease-in-out;
}

:deep(.el-progress__text) {
  font-size: 14px !important;
}
</style>