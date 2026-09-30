<!-- frontend/src/App.vue -->
<template>
  <div class="container">
    <h1>OCR Document Scanner</h1>
    
    <form @submit.prevent="submitScan">
      <div class="form-group">
        <label>Email Address:</label>
        <input type="email" v-model="email" required placeholder="user@example.com" />
      </div>

      <div class="form-group">
        <label>Scan Mode:</label>
        <select v-model="scanType">
          <option value="single">Single Page (Real-Time)</option>
          <option value="multi">Multi-Page (Batch Process)</option>
        </select>
      </div>

      <div class="form-group">
        <label>Provide Documents:</label>
        <div class="action-buttons">
          
          <!-- Camera Capture (Mobile Native) -->
          <label class="action-btn camera-btn">
            📷 Take Picture
            <input 
              type="file" 
              @change="handleFileUpload" 
              accept="image/*" 
              capture="environment" 
              style="display: none;" 
            />
          </label>

          <!-- Standard Gallery/File Upload -->
          <label class="action-btn upload-btn">
            📂 Choose Files
            <input 
              type="file" 
              @change="handleFileUpload" 
              accept="image/jpeg, image/png, image/webp"
              :multiple="scanType === 'multi'"
              style="display: none;" 
            />
          </label>
        </div>
        
        <p class="file-count" v-if="files.length > 0">
          {{ files.length }} file(s) ready for extraction.
        </p>
      </div>

      <!-- Human Verification (Math CAPTCHA) -->
      <div class="form-group captcha-group">
        <label>Human Verification:</label>
        <div class="captcha-box">
          <span>What is <strong>{{ num1 }} + {{ num2 }}</strong>?</span>
          <input 
            type="number" 
            v-model.number="captchaAnswer" 
            required 
            placeholder="Answer"
          />
        </div>
      </div>

      <button type="submit" :disabled="isSubmitting || files.length === 0">
        {{ isSubmitting ? 'Processing...' : 'Submit Scan' }}
      </button>
    </form>

    <div v-if="resultText" class="result-box">
      <h3>Extracted Text:</h3>
      <p>{{ resultText }}</p>
    </div>

    <div v-if="statusMessage" class="status-box" :class="{ 'error-text': isError }">
      <p>{{ statusMessage }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const email = ref('');
const scanType = ref('single');
const files = ref([]);
const isSubmitting = ref(false);
const resultText = ref('');
const statusMessage = ref('');
const isError = ref(false);

// CAPTCHA State
const num1 = ref(0);
const num2 = ref(0);
const captchaAnswer = ref('');
const captchaExpected = ref(0);

const generateCaptcha = () => {
  num1.value = Math.floor(Math.random() * 10) + 1;
  num2.value = Math.floor(Math.random() * 10) + 1;
  captchaExpected.value = num1.value + num2.value;
  captchaAnswer.value = '';
};

// Initialize CAPTCHA on component mount
onMounted(() => {
  generateCaptcha();
});

const handleFileUpload = (event) => {
  files.value = Array.from(event.target.files);
};

const submitScan = async () => {
  isError.value = false;
  statusMessage.value = '';
  resultText.value = '';

  // Validate Human Verification
  if (captchaAnswer.value !== captchaExpected.value) {
    isError.value = true;
    statusMessage.value = 'Incorrect human verification answer. Please try again.';
    generateCaptcha(); // Reset test on failure
    return;
  }

  isSubmitting.value = true;

  const formData = new FormData();
  formData.append('email', email.value);
  formData.append('scan_type', scanType.value);
  formData.append('os_version', navigator.userAgent);
  
  // Passing a simulated token indicating the math challenge was passed
  const validationToken = btoa(`passed_math_challenge_${Date.now()}`);
  formData.append('human_validation_token', validationToken); 

  files.value.forEach((file) => {
    formData.append('document_images', file);
  });

  try {
    const baseUrl = import.meta.env.API_BASE_URL || '';
    const endpoint = `https://ocr-lakehouse-app.onrender.com//api/submit-scan`;

    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData, 
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Server error');

    if (response.status === 200) {
      resultText.value = data.text;
      statusMessage.value = `Success! Session ID: ${data.session_id}`;
    } else if (response.status === 202) {
      statusMessage.value = `${data.message} Session ID: ${data.session_id}`;
    }

    // Reset form after successful submission
    files.value = [];
    generateCaptcha();

  } catch (error) {
    console.error(error);
    isError.value = true;
    statusMessage.value = `Error: ${error.message}`;
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.container { 
  max-width: 600px; 
  margin: 2rem auto; 
  font-family: sans-serif; 
  padding: 0 1rem;
}
.form-group { 
  margin-bottom: 1.5rem; 
  display: flex; 
  flex-direction: column; 
}
input, select { 
  padding: 0.5rem; 
  margin-top: 0.5rem; 
  border: 1px solid #ccc;
  border-radius: 4px;
}
.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}
.action-btn {
  flex: 1;
  padding: 0.75rem;
  text-align: center;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s;
  box-sizing: border-box;
}
.camera-btn {
  background-color: #2c3e50;
  color: white;
}
.upload-btn {
  background-color: #e2e8f0;
  color: #2c3e50;
}
.file-count {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: #42b883;
  font-weight: bold;
}
.captcha-group {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}
.captcha-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.5rem;
}
.captcha-box input {
  width: 100px;
  margin-top: 0;
}
button[type="submit"] { 
  width: 100%;
  padding: 0.75rem; 
  background-color: #42b883; 
  color: white; 
  border: none; 
  border-radius: 6px;
  cursor: pointer; 
  font-size: 1rem;
  font-weight: bold;
}
button[type="submit"]:disabled { 
  background-color: #a0d8c0; 
  cursor: not-allowed;
}
.result-box { 
  margin-top: 2rem; 
  padding: 1rem; 
  background-color: #f8f9fa; 
  border-left: 4px solid #42b883; 
}
.status-box { 
  margin-top: 1rem; 
  font-weight: bold; 
  color: #42b883; 
}
.error-text {
  color: #dc3545;
}
</style>