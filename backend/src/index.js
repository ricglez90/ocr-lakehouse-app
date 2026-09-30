require('dotenv').config(); // MUST BE LINE 1

const express = require('express');
const multer = require('multer');
const { createClient } = require('@supabase/supabase-js');
const { v4: uuidv4 } = require('uuid');
const Tesseract = require('tesseract.js');

const app = express();
app.use(express.json());

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

const upload = multer({ 
    storage: multer.memoryStorage(),
    limits: { fileSize: 5 * 1024 * 1024 } 
});

app.post('/api/submit-scan', upload.array('document_images', 10), async (req, res) => {
    try {
        const { email, os_version, human_validation_token, scan_type } = req.body;
        const files = req.files;

        if (!files || files.length === 0) return res.status(400).json({ error: 'No images provided' });
        
        const sessionId = uuidv4();

        const { error: sessionError } = await supabase.from('telemetry_sessions').insert({
            session_id: sessionId,
            user_email: email,
            os_version: os_version,
            human_validation_score: 0.9 
        });

        if (sessionError) throw sessionError;

        if (scan_type === 'single' && files.length === 1) {
            const { data: { text } } = await Tesseract.recognize(files[0].buffer, 'eng');
            
            await supabase.from('ocr_jobs').insert({
                job_id: uuidv4(), session_id: sessionId, page_number: 1, status: 'completed', extracted_text: text
            });

            return res.status(200).json({ text: text, session_id: sessionId });

        } else {
            const pageRecords = [];
            for (let i = 0; i < files.length; i++) {
                const storagePath = `raw_documents/${sessionId}_page_${i + 1}.jpg`;
                const { error: uploadError } = await supabase.storage.from('ocr_bucket').upload(storagePath, files[i].buffer, { contentType: files[i].mimetype });

                if (uploadError) throw uploadError;

                pageRecords.push({
                    job_id: uuidv4(), session_id: sessionId, page_number: i + 1, image_storage_path: storagePath, status: 'pending'
                });
            }

            const { error: jobError } = await supabase.from('ocr_jobs').insert(pageRecords);
            if (jobError) throw jobError;

            return res.status(202).json({ message: 'Images queued for Databricks batch processing.', session_id: sessionId });
        }
    } catch (error) {
        console.error('Pipeline Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Backend running on port ${PORT}`));