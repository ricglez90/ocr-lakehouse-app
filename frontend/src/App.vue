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
        <label>Upload Documents:</label>
        <!-- The 'multiple' attribute dynamically allows batch uploads based on scanType -->
        <input 
          type="file" 
          @change="handleFileUpload" 
          accept="image/jpeg, image/png, image/webp"
          :multiple="scanType === 'multi'"
          required 
        />
      </div>

      <button type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? 'Processing...' : 'Submit Scan' }}
      </button>
    </form>

    <div v-if="resultText" class="result-box">
      <h3>Extracted Text:</h3>
      <p>{{ resultText }}</p>
    </div>

    <div v-if="statusMessage" class="status-box">
      <p>{{ statusMessage }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const email = ref('');
const scanType = ref('single');
const files = ref([]);
const isSubmitting = ref(false);
const resultText = ref('');
const statusMessage = ref('');

// Capture the raw files from the input event
const handleFileUpload = (event) => {
  files.value = Array.from(event.target.files);
};

const submitScan = async () => {

  // Use the production Render URL if available, otherwise fallback to local proxy
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const endpoint = `${baseUrl}/api/submit-scan`;

  const response = await fetch(endpoint, {
    method: 'POST',
    body: formData, 
  });
  isSubmitting.value = true;
  resultText.value = '';
  statusMessage.value = '';

  // 1. Construct the multipart/form-data payload
  const formData = new FormData();
  formData.append('email', email.value);
  formData.append('scan_type', scanType.value);
  
  // Extract OS version natively from the browser
  formData.append('os_version', navigator.userAgent);
  
  // Mocking the CAPTCHA token for the PoC
  formData.append('human_validation_token', 'mock_captcha_token_123'); 

  // The 'document_images' key MUST match the multer upload.array() configuration in Node.js
  files.value.forEach((file) => {
    formData.append('document_images', file);
  });

  try {
    // 2. Transmit to the Node.js Backend (proxied via Vite)
    const response = await fetch('/api/submit-scan', {
      method: 'POST',
      body: formData, 
      // Do NOT set Content-Type header. The browser automatically sets it 
      // with the correct boundary string for multipart/form-data.
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Server error');

    // 3. Handle Synchronous vs Asynchronous UI states
    if (response.status === 200) {
      resultText.value = data.text;
      statusMessage.value = `Success! Session ID: ${data.session_id}`;
    } else if (response.status === 202) {
      statusMessage.value = `${data.message} Session ID: ${data.session_id}`;
    }

  } catch (error) {
    console.error(error);
    statusMessage.value = `Error: ${error.message}`;
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.container { max-width: 600px; margin: 2rem auto; font-family: sans-serif; }
.form-group { margin-bottom: 1.5rem; display: flex; flex-direction: column; }
input, select { padding: 0.5rem; margin-top: 0.5rem; }
button { padding: 0.75rem; background-color: #42b883; color: white; border: none; cursor: pointer; }
button:disabled { background-color: #ccc; }
.result-box { margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-left: 4px solid #42b883; }
.status-box { margin-top: 1rem; font-weight: bold; color: #555; }
</style>